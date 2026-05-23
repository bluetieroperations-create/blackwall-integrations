# Black_Wall + Vercel AI SDK

Wrap any AI SDK tool so Black_Wall vets the call before `execute` runs.

```bash
npm i ai
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

```ts
import { generateText, tool } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';
import { guardTool } from './blackwall-guard';

const sendEmail = tool({
  description: 'Send an email',
  parameters: z.object({ to: z.string(), subject: z.string(), body: z.string() }),
  execute: async ({ to, subject, body }) => {
    // ... your real send ...
    return { sent: true, to };
  },
});

const safeSend = guardTool('send_email', sendEmail, {
  context: { agent_role: 'support bot', user_intent: 'reply to a ticket' },
});

await generateText({
  model: openai('gpt-4o'),
  prompt: 'Email the customer their refund confirmation.',
  tools: { sendEmail: safeSend },
});
```

When the model calls the tool, Black_Wall sees the action first:

- **AUTO** → `execute` runs normally.
- **CONFIRM** → returns a `{ blocked: true, ... }` result (pass `onConfirm: async (v) => ...` to allow with a human in the loop).
- **HUMAN_REQUIRED / STOP** → returns `{ blocked: true, gate, risk_score, red_flags, alternative_actions }` instead of executing.

Blocked calls **return** the verdict rather than throwing, so the model gets it as a
tool result and can pick a safer alternative. Default is **fail closed** (block if the
check errors); pass `failOpen: true` to run the tool when Black_Wall is unreachable.

Works with AI SDK v4 (`parameters`) and v5 (`inputSchema`) — the guard only wraps
`execute`. See [`blackwall-guard.ts`](./blackwall-guard.ts) for the full source.
