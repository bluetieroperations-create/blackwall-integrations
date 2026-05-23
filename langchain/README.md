# Black_Wall + LangChain

Put a pre-action risk check in front of any LangChain tool.

```bash
pip install langchain-core requests
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

```python
from blackwall_guard import guard_tool, ActionBlocked

# `email_tool` is any existing LangChain tool
safe_email = guard_tool(
    email_tool,
    action="send_email",
    context={"agent_role": "support bot", "user_intent": "reply to a ticket"},
)

# Hand the guarded tool to your agent instead of the raw one:
agent = create_react_agent(llm, tools=[safe_email])
```

When the agent calls the tool, Black_Wall sees the action first:

- **AUTO** → the tool runs normally.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=lambda v: ...` to allow with a human in the loop).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags and safer alternatives.

By default the guard **fails closed** (blocks if the check errors). Pass
`fail_open=True` to let the tool run when Black_Wall is unreachable.

See [`blackwall_guard.py`](./blackwall_guard.py) for the full, copy-pasteable source
(run it directly for a live demo).
