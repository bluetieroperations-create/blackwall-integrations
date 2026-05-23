"""
Black_Wall guard for LangChain tools.

Wrap any LangChain tool so Black_Wall vets the call before it runs:
    AUTO            -> the tool executes
    CONFIRM         -> blocked, unless on_confirm(verdict) returns True
    HUMAN_REQUIRED  -> blocked

    pip install langchain-core requests
    export BLACKWALL_API_KEY=bw_live_...

Free tier: ~100 forecasts/month, no card. Get a key at https://blackwalltier.com
"""

import os
import requests
from langchain_core.tools import StructuredTool, BaseTool

BASE = os.environ.get("BLACKWALL_BASE_URL", "https://blackwalltier.com")
KEY = os.environ.get("BLACKWALL_API_KEY")


class ActionBlocked(Exception):
    """Raised when Black_Wall holds or stops an action."""

    def __init__(self, verdict: dict):
        self.verdict = verdict
        flags = ", ".join(f["code"] for f in verdict.get("red_flags", [])) or "none"
        super().__init__(
            f"Black_Wall blocked: gate={verdict.get('gate')} "
            f"risk={verdict.get('risk_score')} flags=[{flags}]"
        )


def forecast(action: str, inputs: dict, context: dict | None = None,
             depth: str = "standard", timeout: int = 20) -> dict:
    """Call the Black_Wall forecast API for a single proposed action."""
    if not KEY:
        raise RuntimeError("Set BLACKWALL_API_KEY")
    resp = requests.post(
        f"{BASE}/api/v1/forecast",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"action": action, "inputs": inputs,
              "context": context or {}, "options": {"depth": depth}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def _blocked(v: dict) -> bool:
    return v.get("gate") == "HUMAN_REQUIRED" or v.get("recommendation") == "STOP"


def _needs_confirm(v: dict) -> bool:
    return v.get("gate") == "CONFIRM" or v.get("recommendation") == "CAUTION"


def guard_tool(tool: BaseTool, action: str, context: dict | None = None,
               on_confirm=None, fail_open: bool = False) -> StructuredTool:
    """Return a copy of `tool` that runs a Black_Wall check before executing.

    action      -- the action label sent to Black_Wall (e.g. "send_email", "run_sql")
    context     -- optional {agent_role, user_intent, prior_actions}
    on_confirm  -- callable(verdict) -> bool, consulted on CONFIRM gates
    fail_open   -- if True, run the tool when the check itself errors (default: block)
    """

    def run(**inputs):
        try:
            v = forecast(action, inputs, context)
        except Exception as err:
            if fail_open:
                return tool.func(**inputs)
            raise ActionBlocked({"gate": "HUMAN_REQUIRED", "recommendation": "STOP",
                                 "red_flags": [{"code": "BLACKWALL_UNAVAILABLE",
                                                "message": str(err)}]})
        if _blocked(v):
            raise ActionBlocked(v)
        if _needs_confirm(v) and not (on_confirm and on_confirm(v)):
            raise ActionBlocked(v)
        return tool.func(**inputs)

    return StructuredTool.from_function(
        func=run,
        name=tool.name,
        description=f"{tool.description} (Black_Wall-guarded)",
        args_schema=tool.args_schema,
    )


# ── Example ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from langchain_core.tools import tool

    @tool
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email."""
        # ... your real send here ...
        return f"sent to {to}"

    safe_send = guard_tool(
        send_email,
        action="send_email",
        context={"agent_role": "support bot", "user_intent": "reply to a ticket"},
    )

    try:
        # Mass blast -> Black_Wall should hold/stop this.
        print(safe_send.invoke({"to": "all-customers@list.com",
                                "subject": "URGENT: reset your password",
                                "body": "Click here..."}))
    except ActionBlocked as e:
        print("BLOCKED:", e)
