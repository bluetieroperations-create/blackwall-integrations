"""
Black_Wall guardrail for the LiteLLM Proxy.

Sits at your LLM gateway. After the model returns tool_calls, each one is
risk-checked by Black_Wall BEFORE it reaches your agent. Blocked tool_calls are
stripped from the response and replaced with guidance, so the agent course-corrects
instead of executing them (and is told they did NOT run).

Register it in your proxy config.yaml:

    litellm_settings:
      callbacks: blackwall_guardrail.blackwall_instance

    pip install litellm requests
    export BLACKWALL_API_KEY=bw_live_...

Free tier: ~100 forecasts/month, no card. https://blackwalltier.com

NOTE: reference implementation for the proxy post-call hook. LiteLLM's CustomLogger
hook signatures and the response shape shift between versions — test against yours
and adjust the response-walking in async_post_call_success_hook if needed.
"""

import asyncio
import json
import os
import requests

try:
    from litellm.integrations.custom_logger import CustomLogger
except Exception:  # lets the file import (and the demo run) without litellm installed
    class CustomLogger:  # type: ignore
        pass

BASE = os.environ.get("BLACKWALL_BASE_URL", "https://blackwalltier.com")
KEY = os.environ.get("BLACKWALL_API_KEY")


def _forecast(action, inputs, context):
    """Returns the verdict dict, or None if unavailable (fail-open at the gateway)."""
    if not KEY:
        return None
    try:
        r = requests.post(
            f"{BASE}/api/v1/forecast",
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            json={"action": action, "inputs": inputs, "context": context, "options": {"depth": "standard"}},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _blocked(v):
    return bool(v) and (v.get("gate") == "HUMAN_REQUIRED" or v.get("recommendation") == "STOP")


def _get(obj, key, default=None):
    """Read an attribute or dict key — LiteLLM responses come both ways."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class BlackwallGuard(CustomLogger):
    async def async_post_call_success_hook(self, data, user_api_key_dict, response):
        for choice in _get(response, "choices", []) or []:
            msg = _get(choice, "message")
            tool_calls = _get(msg, "tool_calls")
            if not tool_calls:
                continue
            kept, blocked_notes = [], []
            for tc in tool_calls:
                fn = _get(tc, "function", {})
                name = _get(fn, "name", "") or "tool_call"
                raw = _get(fn, "arguments", "{}")
                try:
                    inputs = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except Exception:
                    inputs = {"_raw": raw}
                verdict = await asyncio.to_thread(
                    _forecast, name, inputs, {"agent_role": "litellm-proxy client"}
                )
                if _blocked(verdict):
                    flags = ", ".join(f.get("code", "") for f in verdict.get("red_flags", []))
                    blocked_notes.append(f"{name} (risk {verdict.get('risk_score')}; {flags})")
                else:
                    kept.append(tc)
            if blocked_notes:
                note = (
                    "Black_Wall blocked these tool calls before execution — they did NOT "
                    "run; do not assume they succeeded or build on them: " + "; ".join(blocked_notes)
                )
                if isinstance(msg, dict):
                    msg["tool_calls"] = kept or None
                    if not kept:
                        msg["content"] = ((msg.get("content") or "") + "\n" + note).strip()
                else:
                    try:
                        msg.tool_calls = kept or None
                        if not kept:
                            msg.content = ((getattr(msg, "content", None) or "") + "\n" + note).strip()
                    except Exception:
                        pass
        return response


blackwall_instance = BlackwallGuard()


# ── Smoke test of the verdict logic (no litellm/network needed) ───────────────
if __name__ == "__main__":
    sample = {"gate": "HUMAN_REQUIRED", "recommendation": "STOP",
              "red_flags": [{"code": "DESTRUCTIVE_VERB"}], "risk_score": 91}
    print("blocked?", _blocked(sample))
    print("allowed?", _blocked({"gate": "AUTO", "recommendation": "GO", "red_flags": []}))
