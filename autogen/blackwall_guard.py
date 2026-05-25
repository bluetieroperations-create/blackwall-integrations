"""
Black_Wall guard for AutoGen / AG2 tools.

Vet a registered function with a pre-action risk check before it runs:
    AUTO            -> the tool executes
    CONFIRM         -> blocked, unless on_confirm(verdict) returns True
    HUMAN_REQUIRED  -> blocked

Multi-agent swarms are exactly where cascade/collusion risk lives — pass
context (agent_role, user_intent) so Black_Wall can judge the action in context.

    pip install autogen-agentchat requests   # or: pip install ag2 requests
    export BLACKWALL_API_KEY=bw_live_...

Free tier: ~100 forecasts/month, no card. https://blackwalltier.com
"""

import asyncio
import inspect
import os
from functools import wraps
import requests

BASE = os.environ.get("BLACKWALL_BASE_URL", "https://blackwalltier.com")
KEY = os.environ.get("BLACKWALL_API_KEY")


class ActionBlocked(Exception):
    def __init__(self, verdict: dict):
        self.verdict = verdict
        flags = ", ".join(f.get("code", "") for f in verdict.get("red_flags", [])) or "none"
        super().__init__(
            f"Black_Wall blocked: gate={verdict.get('gate')} "
            f"risk={verdict.get('risk_score')} flags=[{flags}]"
        )


def forecast(action, inputs, context=None, depth="standard", timeout=20):
    if not KEY:
        raise RuntimeError("Set BLACKWALL_API_KEY (free key at https://blackwalltier.com)")
    resp = requests.post(
        f"{BASE}/api/v1/forecast",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"action": action, "inputs": inputs, "context": context or {}, "options": {"depth": depth}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def _blocked(v):
    return v.get("gate") == "HUMAN_REQUIRED" or v.get("recommendation") == "STOP"


def _needs_confirm(v):
    return v.get("gate") == "CONFIRM" or v.get("recommendation") == "CAUTION"


def _unavailable(err):
    return {"gate": "HUMAN_REQUIRED", "recommendation": "STOP",
            "red_flags": [{"code": "BLACKWALL_UNAVAILABLE", "message": str(err)}]}


def guard(action, context=None, on_confirm=None, fail_open=False):
    """Wrap a function before registering it with AutoGen so Black_Wall vets it first.

        def transfer_funds(amount_usd: float, to: str) -> str: ...

        guarded = guard(action="make_payment", context={"agent_role": "treasury bot"})(transfer_funds)
        register_function(guarded, caller=assistant, executor=user_proxy,
                          name="transfer_funds", description="...")

    Default is fail-closed (block if the check errors); pass fail_open=True to run
    the tool anyway when Black_Wall is unreachable. Works on sync and async tools.
    """
    def deco(fn):
        def _inputs(args, kwargs):
            inputs = dict(kwargs)
            if args:
                inputs["_args"] = list(args)
            return inputs

        def _decide(v):
            if _blocked(v):
                raise ActionBlocked(v)
            if _needs_confirm(v) and not (on_confirm and on_confirm(v)):
                raise ActionBlocked(v)

        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def awrapper(*args, **kwargs):
                try:
                    v = await asyncio.to_thread(forecast, action, _inputs(args, kwargs), context)
                except Exception as err:
                    if fail_open:
                        return await fn(*args, **kwargs)
                    raise ActionBlocked(_unavailable(err))
                _decide(v)
                return await fn(*args, **kwargs)
            return awrapper

        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                v = forecast(action, _inputs(args, kwargs), context)
            except Exception as err:
                if fail_open:
                    return fn(*args, **kwargs)
                raise ActionBlocked(_unavailable(err))
            _decide(v)
            return fn(*args, **kwargs)
        return wrapper
    return deco


# ── Example (runs without autogen installed) ──────────────────────────────────
if __name__ == "__main__":
    @guard(action="make_payment", context={"agent_role": "treasury bot", "user_intent": "pay an invoice"})
    def transfer_funds(amount_usd: float, to: str) -> str:
        return f"sent ${amount_usd} to {to}"

    try:
        print(transfer_funds(amount_usd=48000, to="new-vendor@unknown.com"))
    except ActionBlocked as e:
        print("BLOCKED:", e)
