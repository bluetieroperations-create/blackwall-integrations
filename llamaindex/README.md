# Black_Wall + LlamaIndex

Vet a LlamaIndex tool with a pre-action risk check before it runs. The read-data-then-act
pattern (RAG → action) is where intent-mismatch and PII risks show up, so gate the
*acting* tools.

```bash
pip install llama-index requests
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

Wrap the function with `guard(...)` when you build the `FunctionTool`:

```python
from llama_index.core.tools import FunctionTool
from blackwall_guard import guard, ActionBlocked

def run_sql(query: str) -> str:
    # ... your real DB logic ...
    return "rows..."

sql_tool = FunctionTool.from_defaults(
    fn=guard(action="run_sql", context={"agent_role": "rag bot", "user_intent": "answer a question"})(run_sql),
    name="run_sql",
    description="Run a read query and return rows.",
)
# pass sql_tool into your FunctionAgent / AgentWorkflow as usual
```

When the agent calls the tool, Black_Wall sees the action first:

- **AUTO** → the tool runs normally.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=lambda v: ...` to allow with a human in the loop).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags and safer alternatives.

Works on sync and async tools. Default is **fail closed** (block if the check errors);
pass `fail_open=True` to run the tool anyway when Black_Wall is unreachable.

See [`blackwall_guard.py`](./blackwall_guard.py) for the full source (run it directly
for a live demo — no LlamaIndex install needed for the demo).
