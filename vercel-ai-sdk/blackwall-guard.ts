/**
 * Black_Wall guard for the Vercel AI SDK.
 *
 * Wrap any AI SDK tool so Black_Wall vets the call before `execute` runs:
 *   AUTO            -> the tool executes
 *   CONFIRM         -> blocked, unless onConfirm(verdict) resolves true
 *   HUMAN_REQUIRED  -> blocked
 *
 * A blocked call returns a structured result (not a throw) so the model sees the
 * verdict and can choose a safer alternative.
 *
 *   npm i ai
 *   export BLACKWALL_API_KEY=bw_live_...
 *
 * Free tier: ~100 forecasts/month, no card. Get a key at https://blackwalltier.com
 */
import type { Tool } from 'ai';

const BASE = process.env.BLACKWALL_BASE_URL ?? 'https://blackwalltier.com';
const KEY = process.env.BLACKWALL_API_KEY;

export interface Verdict {
  id: string;
  recommendation: 'GO' | 'CAUTION' | 'STOP';
  risk_score: number;
  gate: 'AUTO' | 'CONFIRM' | 'HUMAN_REQUIRED';
  reversibility: { class: string; rollback_cost: number };
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

export interface GuardOpts {
  context?: Record<string, unknown>;
  onConfirm?: (v: Verdict) => boolean | Promise<boolean>;
  failOpen?: boolean; // run the tool if the check itself errors (default: block)
}

/**
 * Wrap a tool so every call is vetted by Black_Wall first.
 *
 *   const safeSend = guardTool('send_email', sendEmailTool, {
 *     context: { agent_role: 'support bot', user_intent: 'reply to a ticket' },
 *   });
 */
export function guardTool<T extends Tool>(action: string, toolDef: T, opts: GuardOpts = {}): T {
  const inner = (toolDef as { execute?: (args: unknown, ctx: unknown) => unknown }).execute;
  if (typeof inner !== 'function') return toolDef; // nothing to guard

  const execute = async (args: unknown, ctx: unknown) => {
    let v: Verdict;
    try {
      v = await forecast(action, args, opts.context);
    } catch (err) {
      if (opts.failOpen) return inner(args, ctx);
      return { blocked: true, reason: 'BLACKWALL_UNAVAILABLE', message: String(err) };
    }
    const allow = !blocked(v) && (!needsConfirm(v) || (!!opts.onConfirm && (await opts.onConfirm(v))));
    if (!allow) {
      return {
        blocked: true,
        gate: v.gate,
        risk_score: v.risk_score,
        red_flags: v.red_flags,
        alternative_actions: v.alternative_actions,
        forecast_id: v.id,
      };
    }
    return inner(args, ctx);
  };

  return { ...toolDef, execute } as T;
}
