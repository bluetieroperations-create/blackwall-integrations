# Black_Wall + Coinbase AgentKit

On-chain agents are the highest-stakes agents that exist: once a transfer, swap, or
contract call is broadcast, it's **irreversible** — no chargeback, no reversal, no
support ticket. A pre-action check is the *only* safety net before the chain. Put one
in front of every on-chain action.

```bash
pip install coinbase-agentkit requests   # + your agent framework
export BLACKWALL_API_KEY=bw_live_...      # free key at https://blackwalltier.com
```

Put `@guard` on the function that performs the on-chain action (a Coinbase AgentKit
action provider, or your own web3 wrapper):

```python
from blackwall_guard import guard, ActionBlocked

@guard(action="transfer_crypto", context={"agent_role": "treasury agent", "user_intent": "pay a supplier"})
def transfer(asset: str, amount: float, to_address: str, network: str = "base") -> str:
    # your Coinbase AgentKit transfer / swap / contract call
    ...
```

When the agent calls it, Black_Wall sees the action first:

- **AUTO** → it's broadcast.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=lambda v: ...` to allow with a human approving).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags (e.g. `AMOUNT_OUT_OF_BAND`, `RECIPIENT_UNVERIFIED`, `IRREVERSIBLE_NO_BACKUP`) — *before* anything hits the chain.

## The demo

```
$ python blackwall_guard.py
BLOCKED: Black_Wall blocked this action — it was NOT executed; do not assume it
succeeded or build on it. gate=HUMAN_REQUIRED risk=88 flags=[AMOUNT_OUT_OF_BAND, RECIPIENT_UNVERIFIED]
```

A 50,000 USDC transfer to an unverified address is held before it's broadcast.

## Notes

- **Never `fail_open=True` here.** On-chain is irreversible — if the check can't be
  reached, the only safe behavior is to NOT broadcast. Fail-closed is the default.
- Works on sync and async functions.
- The same `@guard` works inside any framework (LangChain, CrewAI, Pydantic AI, etc.).

See [`blackwall_guard.py`](./blackwall_guard.py) for the full source (run it directly
for the demo — no Coinbase install needed for the demo).
