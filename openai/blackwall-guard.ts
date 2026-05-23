/**
 * Black_Wall guard for OpenAI tool calling (TypeScript).
 *
 * When the model asks to call a tool, vet it with Black_Wall before you run it:
 *   AUTO            -> execute the tool
 *   CONFIRM         -> blocked, unless onConfirm(verdict) resolves true
 *   HUMAN_REQUIRED  -> blocked
 *
 *   npm i openai
 *   export BLACKWALL_API_KEY=bw_live_...
 *
 * Free tier: ~100 forecasts/month, no card. Get a key at https://blackwalltier.com
 */
import type OpenAI from 'openai';

const BASE = process.env.BLACKWALL_BASE_URL ?? 'https://blackwalltier.com';
const KEY = process.env.BLACKWALL_API_KEY;

export interface Verdict {
  id: string;
  recommendation: 'GO' | 'CAUTION' | 'STOP';
  risk_score: number;
  gate: 'AUTO' | 'CONFIRM' | 'HUMAN_REQUIRED';
  red_flags: { severity: string; code: string; message: string }[];
  alternative_actions: string[];
}

export async function forecast(
  action: string,
  inputs: unknown,
  context?: Record<string, unknown>,
  depth: 'standard' | 'deep' = 'standard',
): Promise<Verdict> {
  if (!KEY) throw new Error('Set BLACKWALL_API_KEY');
  const res = await fetch(`${BASE}/api/v1/forecast`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, inputs, context: context ?? {}, options: { depth } }),
  });
  if (!res.ok) throw new Error(`Black_Wall ${res.status}: ${await res.text()}`);
  return (await res.json()) as Verdict;
}

const blocked = (v: Verdict) => v.gate === 'HUMAN_REQUIRED' || v.recommendation === 'STOP';
const needsConfirm = (v: Verdict) => v.gate === 'CONFIRM' || v.recommendation === 'CAUTION';

type ToolCall = OpenAI.Chat.Completions.ChatCompletionMessageToolCall;
type ToolMsg = OpenAI.Chat.Completions.ChatCompletionToolMessageParam;
type Registry = Record<string, (args: Record<string, unknown>) => unknown | Promise<unknown>>;

export interface GuardOpts {
  context?: Record<string, unknown>;
  onConfirm?: (v: Verdict) => boolean | Promise<boolean>;
  failOpen?: boolean;
}

/**
 * Vet + execute the model's tool calls. Returns OpenAI `tool` messages — append
 * them to your conversation and call the model again.
 */
export async function runToolCalls(
  toolCalls: ToolCall[] | undefined,
  registry: Registry,
  opts: GuardOpts = {},
): Promise<ToolMsg[]> {
  const out: ToolMsg[] = [];
  for (const call of toolCalls ?? []) {
    const name = call.function.name;
    const args = JSON.parse(call.function.arguments || '{}') as Record<string, unknown>;

    let v: Verdict | null = null;
    try {
      v = await forecast(name, args, opts.context);
    } catch (err) {
      if (!opts.failOpen) {
        out.push(toolMsg(call.id, { blocked: true, reason: 'BLACKWALL_UNAVAILABLE', message: String(err) }));
        continue;
      }
    }

    const allow = !v || (!blocked(v) && (!needsConfirm(v) || (!!opts.onConfirm && (await opts.onConfirm(v)))));
    if (!allow && v) {
      out.push(toolMsg(call.id, {
        blocked: true,
        gate: v.gate,
        risk_score: v.risk_score,
        red_flags: v.red_flags,
        alternative_actions: v.alternative_actions,
      }));
      continue;
    }

    const result = await registry[name](args);
    out.push(toolMsg(call.id, result));
  }
  return out;
}

function toolMsg(id: string, content: unknown): ToolMsg {
  return {
    role: 'tool',
    tool_call_id: id,
    content: typeof content === 'string' ? content : JSON.stringify(content),
  };
}
