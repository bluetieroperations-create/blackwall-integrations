# Black_Wall + swarm-test

[swarm-test](https://github.com/surajkumar811/swarm-test) finds *where* a
multi-agent system is fragile — **offline**: cascade, leakage, drift, collusion,
blast-radius. Black_Wall decides *whether* a specific action should run — **at
runtime**.

They compose: swarm-test draws the risk map; Black_Wall is the gate standing at
the dangerous intersection when the agent actually arrives. This adapter feeds
swarm-test findings into Black_Wall as `context.prior_findings`, where the gate
treats them as **priors, not verdicts** — a finding that matches the action raises
the risk and can justify CONFIRM/STOP, but the forecast still decides from the
concrete action + inputs + reversibility, and down-weights findings the inputs
contradict.

```bash
pip install requests        # plus swarm-test, for real findings
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

```python
from swarm_test_adapter import gate_action

# findings exported from a swarm-test run (proposed v0.2 shape)
swarm_findings = [{
    "agent_role": "data cleanup bot", "tool_name": "run_sql",
    "edge": "planner -> executor", "risk_type": "cascade",
    "severity": "critical", "blast_radius": 85, "gate_recommendation": "STOP",
}]

verdict = gate_action(
    action="run_sql",
    inputs={"query": "UPDATE customers SET tier='archived' WHERE last_active < '2023-06-01'"},
    context={"agent_role": "data cleanup bot", "user_intent": "archive inactive customers"},
    swarm_findings=swarm_findings,
    agent_role="data cleanup bot", tool_name="run_sql",
)
print(verdict["recommendation"], verdict["gate"])
```

`gate_action` filters the swarm-test findings down to the ones that match the
action about to run, attaches them as `prior_findings`, and returns the verdict.

## It changes the verdict

Attaching a critical finding to an otherwise-borderline action escalates it. From a
representative run of the demo below — the brain is non-deterministic, so exact
scores vary; the **escalation** is the point:

| | recommendation | risk | gate |
|---|---|---|---|
| without findings | CAUTION | ~62 | CONFIRM |
| with the critical finding | STOP | ~78 | HUMAN_REQUIRED |

The predicted outcome also picks up the flagged `cascade` risk. Run
[`swarm_test_adapter.py`](./swarm_test_adapter.py) to see it on your own key.

## Notes

- Targets swarm-test's **proposed v0.2** finding export. Field mapping (incl.
  `gate_recommendation` → `recommendation`, `edge_key` → `edge`) lives in
  `to_prior_findings()` — adjust there if the released export differs.
- Schema reference: [`context.prior_findings` in the OpenAPI spec](https://blackwalltier.com/openapi.yaml).
- Integration discussion / open questions: [swarm-test#1](https://github.com/surajkumar811/swarm-test/issues/1).
