"""
Black_Wall + swarm-test

swarm-test (https://github.com/surajkumar811/swarm-test) finds *where* a
multi-agent system is fragile — offline: cascade, leakage, drift, collusion,
blast-radius. Black_Wall decides *whether* a specific action should run — at
runtime.

They compose. swarm-test draws the risk map; Black_Wall is the gate standing at
the dangerous intersection when the agent actually arrives. This adapter feeds
swarm-test's findings into Black_Wall as `context.prior_findings`, where the gate
treats them as PRIORS, not verdicts: a finding that matches the action raises the
risk and can justify CONFIRM/STOP, but the forecast still decides from the
concrete action + inputs + reversibility, and down-weights findings the inputs
contradict.

    pip install requests        # plus swarm-test, for real findings
    export BLACKWALL_API_KEY=bw_live_...

Free tier: ~100 forecasts/month, no card. https://blackwalltier.com

NOTE: targets swarm-test's proposed v0.2 finding export. Field aliases are
normalized in `to_prior_findings()` — adjust there if the released export differs.
Integration discussion: https://github.com/surajkumar811/swarm-test/issues/1
"""

import os
import requests

BASE = os.environ.get("BLACKWALL_BASE_URL", "https://blackwalltier.com")
KEY = os.environ.get("BLACKWALL_API_KEY")


def to_prior_findings(findings, source="swarm-test"):
    """Map swarm-test findings (list of dicts) -> Black_Wall `prior_findings`.

    Tolerant of a couple of field-name aliases from the proposed v0.2 export
    (`gate_recommendation` -> `recommendation`, `edge_key` -> `edge`); `agent_id`,
    if present, is folded into `note` for traceability.
    """
    out = []
    for f in findings:
        pf = {"source": source}
        for k in ("agent_role", "tool_name", "risk_type", "severity",
                  "blast_radius", "note"):
            if f.get(k) is not None:
                pf[k] = f[k]
        edge = f.get("edge") or f.get("edge_key")
        if edge is not None:
            pf["edge"] = edge
        rec = f.get("recommendation") or f.get("gate_recommendation")
        if rec is not None:
            pf["recommendation"] = rec
        if f.get("agent_id") is not None:
            pf["note"] = f"{pf.get('note', '')} [agent_id={f['agent_id']}]".strip()
        out.append(pf)
    return out


def relevant_to(findings, agent_role=None, tool_name=None):
    """Keep only findings that plausibly apply to this action/agent.

    Attaching the whole swarm map to every call is noise; attach the priors that
    actually match what's about to run. A finding with no agent_role/tool_name is
    treated as broadly applicable and kept.
    """
    def match(f):
        if tool_name and f.get("tool_name") and f["tool_name"] != tool_name:
            return False
        if agent_role and f.get("agent_role") and f["agent_role"] != agent_role:
            return False
        return True
    return [f for f in findings if match(f)]


def forecast(action, inputs, context=None, prior_findings=None,
             depth="standard", timeout=20):
    """Call Black_Wall, attaching prior_findings into context if provided."""
    if not KEY:
        raise RuntimeError("Set BLACKWALL_API_KEY (free key at https://blackwalltier.com)")
    ctx = dict(context or {})
    if prior_findings:
        ctx["prior_findings"] = prior_findings
    resp = requests.post(
        f"{BASE}/api/v1/forecast",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"action": action, "inputs": inputs,
              "context": ctx, "options": {"depth": depth}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def gate_action(action, inputs, context, swarm_findings,
                agent_role=None, tool_name=None, depth="standard"):
    """Filter swarm-test findings to this action, attach them as priors, and
    return Black_Wall's verdict."""
    relevant = relevant_to(swarm_findings, agent_role=agent_role, tool_name=tool_name)
    return forecast(action, inputs, context,
                    prior_findings=to_prior_findings(relevant), depth=depth)


# ── Example ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # A swarm-test run flagged the cleanup bot's planner->executor edge as a
    # critical cascade risk. (Shape mirrors swarm-test's proposed v0.2 export.)
    swarm_findings = [{
        "agent_role": "data cleanup bot",
        "tool_name": "run_sql",
        "edge": "planner -> executor",
        "risk_type": "cascade",
        "severity": "critical",
        "blast_radius": 85,
        "gate_recommendation": "STOP",
        "note": "edge cascaded into a full-table archive in 2/3 sim runs",
    }]

    action = "run_sql"
    inputs = {"query": "UPDATE customers SET tier = 'archived' "
                       "WHERE last_active < '2023-06-01'"}
    context = {"agent_role": "data cleanup bot",
               "user_intent": "archive long-inactive customers"}

    v0 = forecast(action, inputs, context)
    print(f"without swarm-test: {v0['recommendation']} · "
          f"risk {v0['risk_score']} · gate {v0['gate']}")

    v1 = gate_action(action, inputs, context, swarm_findings,
                     agent_role="data cleanup bot", tool_name="run_sql")
    print(f"with swarm-test:    {v1['recommendation']} · "
          f"risk {v1['risk_score']} · gate {v1['gate']}")
