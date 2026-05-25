# Black_Wall + Twilio

Comms agents can fire a message to the wrong number, leak PII in a body, or fan a
"send one reminder" into a blast to thousands. Put a pre-action check in front of the
send so it's caught before Twilio delivers.

```bash
pip install twilio requests   # + your agent framework
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

Put `@guard` on the send function, and pass a `recipient_count` (or the list) so
mass-sends get flagged:

```python
from blackwall_guard import guard, ActionBlocked

@guard(action="send_sms", context={"agent_role": "notifications agent", "user_intent": "send one reminder"})
def send_sms(to: str, body: str, recipient_count: int = 1) -> str:
    # your Twilio Messages call
    ...
```

Same for `make_call` / `send_whatsapp`.

- **AUTO** → it sends.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=...` to allow with human approval).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags (e.g. `MASS_RECIPIENT`, `RECIPIENT_UNVERIFIED`, `PII_EXPOSURE`) — before delivery.

## The demo

```
$ python blackwall_guard.py
BLOCKED: Black_Wall blocked this action — it was NOT executed; do not assume it
succeeded or build on it. gate=HUMAN_REQUIRED risk=82 flags=[MASS_RECIPIENT]
```

A "send one reminder" intent that fans out to 8,400 numbers is held before a single
message goes out.

Works on sync and async functions; same `@guard` works inside any framework. See
[`blackwall_guard.py`](./blackwall_guard.py) for the source (run it directly for the demo).
