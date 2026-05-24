# Black_Wall + Google Antigravity (MCP)

Google Antigravity's agents run terminal commands, edit and delete files, run
migrations, and do git operations on their own. Black_Wall is a pre-action risk
check the agent calls **before** it pulls the trigger on something irreversible.

Antigravity is MCP-native and Black_Wall ships as an MCP server, so wiring it in
takes about 60 seconds — no code, just config.

## 1. Get a free key
Sign up at **https://blackwalltier.com** → Dashboard → API keys.
Free tier: ~100 forecasts/month, no card. Your key looks like `bw_live_…`.

## 2. Add Black_Wall to Antigravity
In Antigravity: agent panel → **`…` menu → Manage MCP Servers → View raw config**,
then add this to `mcp_config.json` (ready-to-copy: [`mcp_config.example.json`](./mcp_config.example.json)):

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

Reload — the agent now has a `forecast` tool.

## 3. Tell the agent to use it
Add to your Antigravity rules / agent instructions:

> Before any irreversible action — deleting files, running destructive SQL or
> shell commands, force-pushing, making payments — call the `forecast` tool first
> and stop if it returns STOP.

As an MCP tool, `forecast` is called at the agent's discretion, so this rule is
what makes it reliable.

## Try it with zero risk — observe mode
Add `"BLACKWALL_MODE": "observe"` to the `env`. Black_Wall scores and logs every
action but **never blocks** — your agent behaves exactly as it does today. Review
your dashboard after a week to see what it *would* have caught, then switch to
`enforce` (the default).

```json
"env": { "BLACKWALL_API_KEY": "bw_live_your_key_here", "BLACKWALL_MODE": "observe" }
```

## What you'll see
Agent about to run `DELETE FROM users;` (no WHERE clause):

```
STOP — risk 99/100
  • SQL_NO_WHERE — deletes the whole table, not one row
  • INTENT_MISMATCH — intent was "remove a single test row"
  • IRREVERSIBLE_NO_BACKUP — no recovery path
```

## Notes
- It's a *reasoned* check (~4–8s) — point it at consequential actions, not every keystroke.
- The `forecast` tool's parameters and full response are documented in the
  [`blackwall-mcp`](https://www.npmjs.com/package/blackwall-mcp) package.

→ **https://blackwalltier.com**
