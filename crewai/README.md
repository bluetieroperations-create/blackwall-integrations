# Black_Wall + CrewAI

Vet a CrewAI tool with a pre-action risk check before it runs.

```bash
pip install crewai requests
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

```python
from crewai.tools import tool
from blackwall_guard import guard, ActionBlocked

@tool("make_payment")
@guard(action="make_payment",
       context={"agent_role": "AP bot", "user_intent": "pay an invoice"})
def make_payment(amount_usd: float, to: str, memo: str = "") -> str:
    # ... your real payment logic ...
    return f"paid ${amount_usd} to {to}"
```

Stack `@guard` **below** CrewAI's `@tool` so CrewAI registers the guarded callable.
When the agent invokes the tool, Black_Wall sees the action first:

- **AUTO** → the tool runs normally.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=lambda v: ...` to allow with a human in the loop).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags and safer alternatives.

Default is **fail closed** (block if the check errors); pass `fail_open=True` to run
the tool anyway when Black_Wall is unreachable.

See [`blackwall_guard.py`](./blackwall_guard.py) for the full source (run it directly
for a live demo — no CrewAI install needed for the demo).
