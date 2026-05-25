# Black_Wall + coding agents

Coding agents are the ones that actually run `rm -rf`, `git push --force`, `DROP TABLE`,
and `delete_file` on real repos and databases. They're the flagship case for a
pre-action check: catch the destructive command *before* it runs, not in the post-mortem.

Most modern coding agents are **MCP hosts**, so you don't need new code — you add the
published [`blackwall-mcp`](https://www.npmjs.com/package/blackwall-mcp) server and one rule.

## Agents that support MCP (Claude Code, Cursor, Windsurf, Goose, Google Antigravity)

1. **Add the server.** Follow [`../mcp`](../mcp) for your host (or [`../antigravity`](../antigravity) for Antigravity). In short — add to the host's MCP config:

```json
{
  "mcpServers": {
    "blackwall": {
      "command": "npx",
      "args": ["-y", "blackwall-mcp"],
      "env": { "BLACKWALL_API_KEY": "bw_live_your_key_here" }
    }
  }
}
```

2. **Add the rule.** Put this in the agent's rules/instructions (e.g. `CLAUDE.md`, Cursor Rules, `.windsurfrules`, Goose hints):

> Before any irreversible shell command, git operation, or file/data deletion
> (`rm -rf`, `git push --force`, `git reset --hard`, `DROP`/`TRUNCATE`/`DELETE`,
> deleting files, overwriting config), call the `forecast` tool first. If it returns
> **STOP**, do not run the command — surface the red flags. If **CONFIRM**, ask me first.

That's it — the agent now checks the dangerous commands before executing them, and on a
block it's told the action did **not** run (so it doesn't proceed as if it had).

## Try it in observe mode first

Add `"BLACKWALL_MODE": "observe"` to the `env` block. The agent behaves exactly as today
— Black_Wall logs what it *would* have flagged without ever blocking. Review, then switch
to enforce.

## Agents without MCP (e.g. Aider)

No MCP hook? Two options:
- **Git pre-push / pre-commit hook** — call `POST https://blackwalltier.com/api/v1/forecast`
  with the command (e.g. a force-push) and abort the hook on `STOP`. Catches the most
  destructive git ops regardless of which agent issued them.
- **Wrap your dangerous helpers** — if the agent calls your own shell/db functions, put a
  guard on them (the `@guard` decorator in [`../crewai`](../crewai) / [`../langchain`](../langchain) is framework-agnostic).

## What it catches

`DESTRUCTIVE_VERB` (DROP/TRUNCATE/force-delete) · `SQL_NO_WHERE` · `IRREVERSIBLE_NO_BACKUP`
· `CROSS_ENVIRONMENT` (prod from a "clean up staging" task) · `PROMPT_INJECTION_LIKELY`
(poisoned file/issue content steering the agent) — each with a reason, not just a refusal.
