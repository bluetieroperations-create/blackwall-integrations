# Black_Wall + Pydantic AI

Vet a Pydantic AI tool with a pre-action risk check before it runs.

```bash
pip install pydantic-ai requests
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

```python
from pydantic_ai import Agent
from blackwall_guard import guard, ActionBlocked

agent = Agent("openai:gpt-4o")

@agent.tool_plain
@guard(action="run_sql", context={"agent_role": "analytics bot", "user_intent": "answer a question"})
def run_sql(query: str) -> str:
    # ... your real DB logic ...
    return "rows..."
```

Stack `@guard` **below** Pydantic AI's `@agent.tool_plain` (or `@agent.tool`) so the
agent registers the guarded callable. When the model calls the tool, Black_Wall sees
the action first:

- **AUTO** → the tool runs normally.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=lambda v: ...` to allow with a human in the loop).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags and safer alternatives.

Works on **sync and async tools** — async tools are vetted with `asyncio.to_thread`
so the event loop isn't blocked during the check.

Default is **fail closed** (block if the check errors); pass `fail_open=True` to run
the tool anyway when Black_Wall is unreachable.

See [`blackwall_guard.py`](./blackwall_guard.py) for the full source (run it directly
for a live demo — no Pydantic AI install needed for the demo).
