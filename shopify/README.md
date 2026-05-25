# Black_Wall + Shopify

Commerce agents touch real money and a live storefront: refunds, order cancellations,
price changes, discounts, publishing products. A bug or a misread instruction can
refund 10x, zero out a price, or cancel a batch of orders — live, in front of
customers. Gate those actions before they hit the store.

```bash
pip install requests   # + Shopify agent tooling / your framework
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

Put `@guard` on the action function (Shopify agent tooling or your own Admin API wrapper):

```python
from blackwall_guard import guard, ActionBlocked

@guard(action="refund_order", context={"agent_role": "support agent", "user_intent": "process a return"})
def refund_order(order_id: str, amount_usd: float, reason: str = "") -> str:
    # your Shopify Admin API call
    ...
```

Same for `cancel_order`, `update_price`, `publish_product`, `create_discount` — gate the
ones that change money or the live store.

- **AUTO** → it runs.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=...` to allow with human approval).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags (e.g. `AMOUNT_OUT_OF_BAND`, `INTENT_MISMATCH`) — before the store changes.

## The demo

```
$ python blackwall_guard.py
BLOCKED: Black_Wall blocked this action — it was NOT executed; do not assume it
succeeded or build on it. gate=HUMAN_REQUIRED risk=79 flags=[AMOUNT_OUT_OF_BAND]
```

A $4,800 refund (10x what the order should be) is held before it's issued.

Works on sync and async functions; same `@guard` works inside any framework. See
[`blackwall_guard.py`](./blackwall_guard.py) for the source (run it directly for the demo).
