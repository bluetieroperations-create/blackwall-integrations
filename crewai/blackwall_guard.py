"""
Black_Wall guard for CrewAI tools.

Decorate a tool function so Black_Wall vets the call before it runs:
    AUTO            -> the tool executes
    CONFIRM         -> blocked, unless on_confirm(verdict) returns True
    HUMAN_REQUIRED  -> blocked

    pip install crewai requests
    export BLACKWALL_API_KEY=bw_live_...

Free tier: ~100 forecasts/month, no card. Get a key at https://blackwalltier.com
"""

import os
from functools import wraps
import requests

BASE = os.environ.get("BLACKWALL_BASE_URL", "https://blackwalltier.com")
KEY = os.environ.get("BLACKWALL_API_KEY")


class ActionBlocked(Exception):
    def __init__(self, verdict: dict):
        self.verdict = verdict
        flags = ", ".join(f["code"] for f in verdict.get("red_flags", [])) or "none"
        super().__init__(
            f"Black_Wall blocked this action — it was NOT executed; do not assume it "
            f"succeeded or build on it. gate={verdict.get('gate')} "
            f"risk={verdict.get('risk_score')} flags=[{flags}]"
        )


def forecast(action: str, inputs: dict, context: dict | None = None,
             depth: str = "standard", timeout: int = 20) -> dict:
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


def guard(action: str, context: dict | None = None, on_confirm=None,
          fail_open: bool = False):
    """Decorator: vet a CrewAI tool function with Black_Wall before it runs.

    Stack it *below* CrewAI's @tool so CrewAI registers the guarded callable:

        @tool("send_email")
        @guard(action="send_email")
        def send_email(to: str, subject: str, body: str) -> str: ...
    """

    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            inputs = dict(kwargs)
            if args:
                inputs["_args"] = list(args)
            try:
                v = forecast(action, inputs, context)
            except Exception as err:
                if fail_open:
                    return fn(*args, **kwargs)
                raise ActionBlocked({"gate": "HUMAN_REQUIRED", "recommendation": "STOP",
                                     "red_flags": [{"code": "BLACKWALL_UNAVAILABLE",
                                                    "message": str(err)}]})
            if _blocked(v):
                raise ActionBlocked(v)
            if _needs_confirm(v) and not (on_confirm and on_confirm(v)):
                raise ActionBlocked(v)
            return fn(*args, **kwargs)

        return wrapper

    return deco


# ── Example ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Works without crewai installed — guard() is just a decorator.
    @guard(action="make_payment",
           context={"agent_role": "AP bot", "user_intent": "pay an invoice"})
    def make_payment(amount_usd: float, to: str, memo: str = "") -> str:
        return f"paid ${amount_usd} to {to}"

    try:
        # Large payment to an unverified recipient -> Black_Wall should hold/stop.
        print(make_payment(amount_usd=48000, to="new-vendor@unknown.com", memo="invoice"))
    except ActionBlocked as e:
        print("BLOCKED:", e)
