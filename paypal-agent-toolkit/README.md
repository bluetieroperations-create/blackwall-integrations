# Black_Wall + PayPal Agent Toolkit

Agents that move money need a check before the money moves. Put a pre-action risk
check in front of every money-moving action — payments, payouts, refunds, invoices —
so a wrong amount or unverified recipient is caught *before* it hits PayPal.

```bash
pip install paypal-agent-toolkit requests   # + your agent framework
export BLACKWALL_API_KEY=bw_live_...         # free key at https://blackwalltier.com
```

Put `@guard` on the money function (a [PayPal Agent Toolkit](https://github.com/paypal/agent-toolkit)
action, or your own PayPal wrapper):

```python
from blackwall_guard import guard, ActionBlocked

@guard(action="make_payment", context={"agent_role": "AP bot", "user_intent": "pay a contractor"})
def send_payout(amount_usd: float, to: str, note: str = "") -> str:
    # your PayPal call — Payouts, Orders, etc.
    ...
```

When the agent calls it, Black_Wall sees the action first:

- **AUTO** → the payout runs.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=lambda v: ...` to allow with a human approving).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags (e.g. `AMOUNT_OUT_OF_BAND`, `RECIPIENT_UNVERIFIED`) — *before* PayPal is called.

## The demo

```
$ python blackwall_guard.py
BLOCKED: Black_Wall blocked this action — it was NOT executed; do not assume it
succeeded or build on it. gate=HUMAN_REQUIRED risk=84 flags=[AMOUNT_OUT_OF_BAND, RECIPIENT_UNVERIFIED]
```

A $48,000 payout to an unverified recipient is held before a cent moves.

## Notes

- For money actions, **fail-closed is the right default** — if the check can't be
  reached, the payout is blocked, not waved through.
- Works on sync and async functions.
- The same `@guard` works inside any framework (LangChain, CrewAI, Pydantic AI, etc.).

See [`blackwall_guard.py`](./blackwall_guard.py) for the full source (run it directly
for the demo — no PayPal install needed for the demo).
