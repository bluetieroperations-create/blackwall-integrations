# Black_Wall + AutoGen / AG2

Vet an AutoGen tool with a pre-action risk check before it runs. Multi-agent swarms
are exactly where cascade/collusion risk lives, so this is a natural place to gate.

```bash
pip install autogen-agentchat requests   # or: pip install ag2 requests
export BLACKWALL_API_KEY=bw_live_...      # free key at https://blackwalltier.com
```

Wrap the function with `guard(...)` **before** you register it, so AutoGen executes
the guarded callable:

```python
from autogen import register_function          # AG2 / classic AutoGen
from blackwall_guard import guard, ActionBlocked

def transfer_funds(amount_usd: float, to: str) -> str:
    # ... your real logic ...
    return f"sent ${amount_usd} to {to}"

guarded = guard(
    action="make_payment",
    context={"agent_role": "treasury bot", "user_intent": "pay an invoice"},
)(transfer_funds)

register_function(
    guarded,
    caller=assistant,        # the agent that proposes the call
    executor=user_proxy,     # the agent that runs it
    name="transfer_funds",
    description="Send a payment to a vendor.",
)
```

When the executor runs the tool, Black_Wall sees the action first:

- **AUTO** → the tool runs normally.
- **CONFIRM** → raises `ActionBlocked` — maps cleanly onto AutoGen's human-in-the-loop (pass `on_confirm=lambda v: ...` to allow with approval).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags and safer alternatives.

Works on sync and async tools. Default is **fail closed** (block if the check errors);
pass `fail_open=True` to run anyway when Black_Wall is unreachable.

See [`blackwall_guard.py`](./blackwall_guard.py) for the full source (run it directly
for a live demo — no AutoGen install needed for the demo).
