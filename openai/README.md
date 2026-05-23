# Black_Wall + OpenAI tool calling

Vet the model's tool calls with a pre-action risk check before you execute them.
Works with the OpenAI Chat Completions tool-calling loop in **Python** or **TypeScript**.

```bash
# Python
pip install openai requests
# TypeScript
npm i openai

export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

## Python

```python
from blackwall_guard import run_tool_calls

resp = client.chat.completions.create(model="gpt-4o", messages=messages, tools=TOOLS)
msg = resp.choices[0].message
messages.append(msg)

# Vet each tool call, run the safe ones, get back `tool` messages.
messages += run_tool_calls(
    msg.tool_calls,
    registry={"run_sql": run_sql, "send_email": send_email},
    context={"agent_role": "data-ops bot", "user_intent": "clean up test data"},
)

# Call the model again with the tool results.
```

## TypeScript

```ts
import { runToolCalls } from './blackwall-guard';

const resp = await client.chat.completions.create({ model: 'gpt-4o', messages, tools });
const msg = resp.choices[0].message;
messages.push(msg);

messages.push(...await runToolCalls(msg.tool_calls, {
  run_sql: ({ statement }) => db.exec(statement as string),
  send_email: (args) => mailer.send(args),
}, { context: { agent_role: 'data-ops bot', user_intent: 'clean up test data' } }));
```

For each tool call:

- **AUTO** → the tool runs; its result goes back to the model.
- **CONFIRM** → returns a `{ blocked: true, ... }` tool result (pass `on_confirm` / `onConfirm` to allow with a human in the loop).
- **HUMAN_REQUIRED / STOP** → returns `{ blocked, gate, risk_score, red_flags, alternative_actions }` instead of running.

Blocked calls come back as normal tool results, so the model sees the verdict and can
choose a safer alternative on the next turn. Default is **fail closed** (block if the
check errors); pass `fail_open` / `failOpen` to run anyway when Black_Wall is unreachable.

Full source: [`blackwall_guard.py`](./blackwall_guard.py) · [`blackwall-guard.ts`](./blackwall-guard.ts)
