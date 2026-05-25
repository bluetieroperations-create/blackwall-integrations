# Black_Wall + cloud / infrastructure

The highest-stakes agent actions there are. An agent that can `terraform destroy`,
`aws s3 rb`, `kubectl delete namespace`, terminate instances, or drop a database will
eventually do one of those at the wrong moment — and the recovery stack (rollback,
backups, insurance) all kicks in *after* the damage. This is the real, expensive
disaster ("an agent wiped prod and the backups in seconds"). Gate the destructive op
**before** it runs.

```bash
pip install requests   # + boto3 / your infra tooling
export BLACKWALL_API_KEY=bw_live_...   # free key at https://blackwalltier.com
```

There's no single "AWS Agent Toolkit," so there are two ways in — use whichever fits
how your agent touches infra.

## Path A — guard your infra helper functions (boto3 / Terraform / kubectl)

Put `@guard` on the functions the agent calls:

```python
from blackwall_guard import guard, ActionBlocked

@guard(action="delete_resource", context={"agent_role": "infra cleanup agent"})
def delete_s3_bucket(bucket: str, environment: str = "staging") -> str:
    # s3.delete_bucket(...)
    ...

@guard(action="run_terraform", context={"agent_role": "platform agent"})
def run_terraform(command: str, workspace: str) -> str:
    # subprocess.run(["terraform", command, ...])  -> command="destroy" gets gated
    ...

@guard(action="kubectl", context={"agent_role": "platform agent"})
def kubectl(args: str) -> str:
    # subprocess.run(["kubectl", *args.split()])    -> "delete namespace prod" gets gated
    ...
```

- **AUTO** → it runs.
- **CONFIRM** → raises `ActionBlocked` (pass `on_confirm=...` for human approval).
- **HUMAN_REQUIRED / STOP** → raises `ActionBlocked` with the red flags — before anything is deleted.

## Path B — MCP rule (AWS official MCP servers, IaC agents)

If your agent reaches infra through MCP (AWS's MCP servers, etc.), add the published
[`blackwall-mcp`](https://www.npmjs.com/package/blackwall-mcp) server (see [`../mcp`](../mcp)) and this rule:

> Before any destructive infrastructure action — delete/terminate a resource,
> `terraform destroy` or `apply` that removes resources, `kubectl delete`, dropping a
> database, deleting a snapshot/backup, or widening IAM — call the `forecast` tool
> first. If it returns **STOP**, do not run it; surface the red flags.

## The demo (the disaster, caught)

```
$ python blackwall_guard.py
BLOCKED: Black_Wall blocked this action — it was NOT executed; do not assume it
succeeded or build on it. gate=HUMAN_REQUIRED risk=93 flags=[CROSS_ENVIRONMENT, DESTRUCTIVE_VERB, IRREVERSIBLE_NO_BACKUP]
```

A "clean up **staging**" task pointed at the **prod backups** bucket is stopped before
the bucket is deleted.

## What it catches

`DESTRUCTIVE_VERB` (destroy/delete/terminate/drop) · `IRREVERSIBLE_NO_BACKUP` (no
snapshot exists) · `CROSS_ENVIRONMENT` (a non-prod task hitting prod) ·
`PERMISSION_ESCALATION` (widening IAM) — each with a reason, not just a refusal.

> **Never `fail_open=True` for destructive infra.** If the check can't be reached, the
> safe behavior is to NOT delete. Fail-closed is the default.
