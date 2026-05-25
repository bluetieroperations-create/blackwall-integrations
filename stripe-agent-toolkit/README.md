# Black_Wall + Stripe Agent Toolkit

Agents that can move money are the highest-stakes agents there are. Put a pre-action
risk check in front of every money-moving action — payments, payouts, refunds,
invoices — so a wrong amount or unverified recipient gets caught *before* it hits
Stripe, not after the funds clear.

```bash
pip install stripe-agent-toolkit requests   # + your agent framework
export BLACKWALL_API_KEY=bw_live_...         # free key at https://blackwalltier.com
```

The pattern: agents almost never get raw Stripe access — you expose money actions as
functions (whether via the [Stripe Agent Toolkit](https://github.com/stripe/agent-toolkit)
or your own wrapper). Put `@guard` on those functions:

```python
from blackwall_guard import guard, ActionBlocked

@guard(action="make_payment", context={"agent_role": "AP bot", "user_intent": "pay an invoice"})
def pay_vendor(amount_usd: float, to: str, memo: str = "") -> str:
    # your Stripe call — PaymentIntent, Payout, Transfer, etc.
    ...
```

When the agent calls it, Black_Wall sees the action first:

- **AUTO** → the payment runs.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=lambda v: ...` to allow with a human approving).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags (e.g. `AMOUNT_OUT_OF_BAND`, `RECIPIENT_UNVERIFIED`) — *before* Stripe is ever called.

## The demo

```
$ python blackwall_guard.py
BLOCKED: Black_Wall blocked this action — it was NOT executed; do not assume it
succeeded or build on it. gate=HUMAN_REQUIRED risk=84 flags=[AMOUNT_OUT_OF_BAND, RECIPIENT_UNVERIFIED]
```

A $48,000 payment to an unverified recipient is held before a cent moves.

## Notes

- For money actions, **fail-closed is the right default** — if the check can't be
  reached, the payment is blocked, not waved through. (`fail_open=True` exists but is
  not recommended here.)
- Works on sync and async functions.
- The same `@guard` works inside any framework (LangChain, CrewAI, Pydantic AI, etc.) —
  apply it to the underlying money function, or use that framework's guard directly.

See [`blackwall_guard.py`](./blackwall_guard.py) for the full source (run it directly
for the demo — no Stripe install needed for the demo).
