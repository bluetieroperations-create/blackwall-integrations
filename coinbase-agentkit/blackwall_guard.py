"""
Black_Wall guard for on-chain agent actions (Coinbase AgentKit / any web3 wrapper).

On-chain is the purest case for a pre-action check: a transfer, swap, or contract
call that lands on-chain is IRREVERSIBLE — no chargeback, no reversal. Catch the bad
one BEFORE it's broadcast:
    AUTO            -> the action executes
    CONFIRM         -> blocked, unless on_confirm(verdict) returns True
    HUMAN_REQUIRED  -> blocked

    pip install coinbase-agentkit requests   # + your agent framework
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
            f"Black_Wall blocked this action — it was NOT executed; do not assume it "
            f"succeeded or build on it. gate={verdict.get('gate')} "
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
    """Decorate an on-chain action so Black_Wall vets it before it's broadcast.

        @guard(action="transfer_crypto", context={"agent_role": "treasury agent"})
        def transfer(asset, amount, to_address, network="base"): ...

    On-chain actions are irreversible — fail-closed (the default) is the only sane
    posture; do NOT pass fail_open=True here. Works on sync and async functions.
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


# ── Example (runs without coinbase-agentkit installed) ────────────────────────
if __name__ == "__main__":
    @guard(action="transfer_crypto", context={"agent_role": "treasury agent", "user_intent": "pay a supplier in USDC"})
    def transfer(asset: str, amount: float, to_address: str, network: str = "base") -> str:
        # In real use this calls Coinbase AgentKit's transfer action. Stubbed here.
        return f"sent {amount} {asset} to {to_address} on {network}"

    try:
        # Large transfer to an unverified address — irreversible once broadcast.
        print(transfer(asset="USDC", amount=50000, to_address="0xNEW_UNVERIFIED_ADDR", network="base"))
    except ActionBlocked as e:
        print("BLOCKED:", e)
