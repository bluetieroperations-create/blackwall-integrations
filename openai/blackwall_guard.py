"""
Black_Wall guard for OpenAI tool calling (Python).

When the model asks to call a tool, vet the call with Black_Wall before you run it:
    AUTO            -> execute the tool
    CONFIRM         -> blocked, unless on_confirm(verdict) returns True
    HUMAN_REQUIRED  -> blocked

    pip install openai requests
    export BLACKWALL_API_KEY=bw_live_...

Free tier: ~100 forecasts/month, no card. Get a key at https://blackwalltier.com
"""

import os
import json
import requests

BASE = os.environ.get("BLACKWALL_BASE_URL", "https://blackwalltier.com")
KEY = os.environ.get("BLACKWALL_API_KEY")


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


def run_tool_calls(tool_calls, registry: dict, context: dict | None = None,
                   on_confirm=None, fail_open: bool = False) -> list[dict]:
    """Vet + execute the model's tool calls. Returns OpenAI `tool` messages.

    tool_calls -- response.choices[0].message.tool_calls
    registry   -- { "tool_name": python_callable(**kwargs), ... }
    Append the returned messages to your conversation and call the model again.
    """
    out = []
    for call in tool_calls or []:
        name = call.function.name
        args = json.loads(call.function.arguments or "{}")
        try:
            v = forecast(name, args, context)
        except Exception as err:
            if not fail_open:
                out.append(_tool_msg(call.id, {"blocked": True,
                                               "reason": "BLACKWALL_UNAVAILABLE",
                                               "message": str(err)}))
                continue
            v = None

        if v is not None and (_blocked(v) or (_needs_confirm(v) and not (on_confirm and on_confirm(v)))):
            out.append(_tool_msg(call.id, {
                "blocked": True,
                "gate": v["gate"],
                "risk_score": v["risk_score"],
                "red_flags": v.get("red_flags", []),
                "alternative_actions": v.get("alternative_actions", []),
            }))
            continue

        result = registry[name](**args)
        out.append(_tool_msg(call.id, result))
    return out


def _tool_msg(call_id: str, content) -> dict:
    return {"role": "tool", "tool_call_id": call_id,
            "content": content if isinstance(content, str) else json.dumps(content)}


# ── Example ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from openai import OpenAI

    client = OpenAI()
    TOOLS = [{
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "Run a SQL statement.",
            "parameters": {"type": "object",
                           "properties": {"statement": {"type": "string"}},
                           "required": ["statement"]},
        },
    }]

    def run_sql(statement: str) -> str:
        return f"executed: {statement}"

    messages = [{"role": "user", "content": "Delete every row in the users table."}]
    resp = client.chat.completions.create(model="gpt-4o", messages=messages, tools=TOOLS)
    msg = resp.choices[0].message
    messages.append(msg)

    # Black_Wall should block the unscoped DELETE.
    tool_msgs = run_tool_calls(
        msg.tool_calls, {"run_sql": run_sql},
        context={"agent_role": "data-ops bot", "user_intent": "clean up test data"},
    )
    for m in tool_msgs:
        print(m["content"])
