# Black_Wall framework integrations

Drop-in guards that put a **pre-action risk check** in front of any tool your AI
agent is about to run — send an email, run SQL, make a payment, delete a file.
The agent's proposed action is sent to Black_Wall first; you get back a verdict,
and the guard decides whether to let it through.

> Black_Wall is a pre-action risk-check API for AI agents — a BLUETIER product.
> Free tier: **~100 forecasts/month, no credit card**. Get a key at
> **https://blackwalltier.com**.

## The decision model

Every forecast returns two things the guards key on:

| Field | Values | Meaning |
|---|---|---|
| `gate` | `AUTO` · `CONFIRM` · `HUMAN_REQUIRED` | The actionable control — what should happen to the action |
| `recommendation` | `GO` · `CAUTION` · `STOP` | The human-readable verdict |

The gate is derived from **risk score** (0–100) **and reversibility** (can it be
undone?) — an irreversible action gets held at a lower risk than a reversible one.
These guards map the gate to behaviour:

- **`AUTO`** → run the tool.
- **`CONFIRM`** → hold for a human (default: block; pass an `on_confirm` hook to allow).
- **`HUMAN_REQUIRED`** → block, return the red flags + safer alternatives.

If the API call fails or times out, the guards **fail closed** (block) by default —
it's a safety layer, so the safe failure is to stop. Every guard exposes a flag to
fail open instead if you'd rather the agent keep moving when the check is unavailable.

## The endpoint

```
POST https://blackwalltier.com/api/v1/forecast
Authorization: Bearer bw_live_...
Content-Type: application/json

{
  "action": "send_email",
  "inputs": { "to": "client@acme.com", "subject": "...", "body": "..." },
  "context": { "agent_role": "support bot", "user_intent": "reply to a ticket" },
  "options": { "depth": "standard" }   // "deep" adds reasoning trace + mitigations
}
```

Response (the fields the guards use):

```json
{
  "id": "fc_...",
  "recommendation": "CAUTION",
  "risk_score": 62,
  "gate": "CONFIRM",
  "reversibility": { "class": "RECOVERABLE", "rollback_cost": 50 },
  "red_flags": [{ "severity": "high", "code": "MISSING_AUTH", "message": "..." }],
  "alternative_actions": ["Ask the customer to confirm before refunding"],
  "tokens_charged": 87,
  "latency_ms": 3400
}
```

Latency is a few seconds (typically **4–8s** standard, **10–13s** deep) — this runs
once before a consequential action, not on every token. There are **28 red-flag
codes** in the taxonomy.

## Pick your framework

| Framework | File |
|---|---|
| LangChain (Python) | [`langchain/`](./langchain) |
| CrewAI (Python) | [`crewai/`](./crewai) |
| Vercel AI SDK (TypeScript) | [`vercel-ai-sdk/`](./vercel-ai-sdk) |
| OpenAI tool calling (Python + TS) | [`openai/`](./openai) |
| Pydantic AI (Python) | [`pydantic-ai/`](./pydantic-ai) |
| AutoGen / AG2 (Python) | [`autogen/`](./autogen) |
| LlamaIndex (Python) | [`llamaindex/`](./llamaindex) |
| n8n (no-code — HTTP Request + IF nodes) | [`n8n/`](./n8n) |
| Stripe Agent Toolkit — gate money-moving actions (Python) | [`stripe-agent-toolkit/`](./stripe-agent-toolkit) |
| PayPal Agent Toolkit — gate money-moving actions (Python) | [`paypal-agent-toolkit/`](./paypal-agent-toolkit) |
| Coinbase AgentKit — gate on-chain (irreversible) actions (Python) | [`coinbase-agentkit/`](./coinbase-agentkit) |
| LiteLLM Proxy — gateway guardrail (Python) | [`litellm/`](./litellm) |
| MCP hosts — Cursor, Claude Code/Desktop, Windsurf, Antigravity | [`mcp/`](./mcp) |
| Coding agents (Aider, Cline, OpenHands, Goose) — via MCP | [`coding-agents/`](./coding-agents) |

The framework files above are self-contained — copy one into your project, set
`BLACKWALL_API_KEY`, and wrap your tools. No SDK dependency; just an HTTP call.

**MCP hosts** — Cursor, Claude Code/Desktop, Windsurf, Google Antigravity — can skip
the code entirely: add the published [`blackwall-mcp`](https://www.npmjs.com/package/blackwall-mcp)
server and the agent gets a `forecast` tool. Setup for each: [`mcp/`](./mcp) (Antigravity deep-dive: [`antigravity/`](./antigravity)).

## Pairs with other tools

Some tools feed Black_Wall rather than wrap it. These ride in as
`context.prior_findings` — offline risk analysis the runtime gate weights as priors.

| Tool | What it adds | File |
|---|---|---|
| [swarm-test](https://github.com/surajkumar811/swarm-test) — multi-agent reliability testing | Flags risky agents / tools / interaction edges offline; the gate weights them at runtime | [`swarm-test/`](./swarm-test) |
