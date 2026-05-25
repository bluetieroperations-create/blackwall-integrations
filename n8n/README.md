# Black_Wall + n8n

Put a pre-action risk check in front of any destructive step in an n8n workflow —
send email, delete rows, make a payment, call a state-changing API. No custom node
needed: it's two built-in nodes (HTTP Request → IF) before the action.

```
… upstream nodes …  →  [HTTP Request: Black_Wall]  →  [IF gate = AUTO?]
                                                          ├─ true  → run the action
                                                          └─ false → stop / notify a human
```

## 1. Store your key as a credential

Get a free key at **https://blackwalltier.com** (~100 forecasts/mo, no card).
In n8n: **Credentials → New → Header Auth**
- Name: `Authorization`
- Value: `Bearer bw_live_your_key_here`

(Don't hardcode the key in the node — use the credential so it isn't exposed.)

## 2. HTTP Request node — call the gate

- **Method:** `POST`
- **URL:** `https://blackwalltier.com/api/v1/forecast`
- **Authentication:** Generic → **Header Auth** → the credential from step 1
- **Body:** JSON →

```json
{
  "action": "send_email",
  "inputs": {
    "to": "={{ $json.to }}",
    "subject": "={{ $json.subject }}",
    "body": "={{ $json.body }}"
  },
  "context": {
    "agent_role": "n8n workflow",
    "user_intent": "={{ $json.intent }}"
  }
}
```

Map `inputs` from whatever the previous nodes produced. The response gives you
`gate`, `recommendation`, `risk_score`, and `red_flags`.

## 3. IF node — gate on the verdict

- **Condition:** `{{ $json.gate }}` **equals** `AUTO`
  - **true** → wire to your real action node (Send Email, Postgres Delete, etc.)
  - **false** → wire to a stop/notify branch (Slack/email a human with `{{ $json.red_flags }}`, or just end the run)

That's it — the destructive node only fires when Black_Wall returns `AUTO`. For
`CONFIRM` / `HUMAN_REQUIRED`, the workflow routes to a human instead of acting.

**Tip:** treat any HTTP error from the gate as a block (fail closed) — add the IF
so the "true" path requires `gate = AUTO` explicitly, so a missing/garbled response
falls through to the safe branch.

> A packaged n8n community node is a possible future addition; the two-node pattern
> above works today with zero install.
