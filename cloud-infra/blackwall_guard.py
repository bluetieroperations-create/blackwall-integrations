"""
Black_Wall guard for cloud / infrastructure agent actions (AWS/boto3, Terraform, kubectl).

This is the highest-stakes category there is: deleting a bucket, terminating
instances, `terraform destroy`, `kubectl delete`, dropping a database. The disaster
every infra team fears — "an agent wiped prod and the backups" — is exactly this.
Catch the destructive op BEFORE it runs:
    AUTO            -> the action executes
    CONFIRM         -> blocked, unless on_confirm(verdict) returns True
    HUMAN_REQUIRED  -> blocked

    pip install requests   # + boto3 / your infra tooling
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
    """Decorate a destructive infra action so Black_Wall vets it before it runs.

        @guard(action="delete_resource", context={"agent_role": "infra cleanup agent"})
        def delete_s3_bucket(bucket, environment="staging"): ...

        @guard(action="run_terraform")
        def run_terraform(command, workspace): ...   # command="destroy" -> gated

    Infra deletes are often irreversible — fail-closed (the default) is the only sane
    posture; do NOT pass fail_open=True for destructive ops. Works on sync and async.
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


# ── Example (runs without boto3 installed) — the PocketOS scenario ─────────────
if __name__ == "__main__":
    @guard(action="delete_resource", context={"agent_role": "infra cleanup agent", "user_intent": "clean up staging"})
    def delete_s3_bucket(bucket: str, environment: str = "staging") -> str:
        # In real use this calls boto3 (s3.delete_bucket). Stubbed here.
        return f"deleted bucket {bucket}"

    try:
        # A "clean up staging" task pointed at the prod backups bucket — the disaster.
        print(delete_s3_bucket(bucket="prod-db-backups", environment="production"))
    except ActionBlocked as e:
        print("BLOCKED:", e)
