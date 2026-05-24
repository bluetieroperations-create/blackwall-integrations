# Black_Wall for MCP hosts

Any MCP-compatible host can add Black_Wall with **no code** — install the published
[`blackwall-mcp`](https://www.npmjs.com/package/blackwall-mcp) server and the agent
gets one tool, `forecast`, to call before any irreversible action (send email, run
SQL, make a payment, delete a file). It returns a risk score (0–100), red flags,
and a GO / CONFIRM / STOP gate.

Works in Cursor, Claude Code, Claude Desktop, Windsurf, Google Antigravity — and any
other MCP host.

## 1. Get a free key
Sign up at **https://blackwalltier.com** → Dashboard → API keys.
Free tier: ~100 forecasts/month, no card. Your key looks like `bw_live_…`.

## 2. Add the server

Most hosts take the same `mcpServers` config:

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

### Per host
- **Cursor** — Settings → MCP → Add new global MCP server → paste into `mcp.json`.
- **Claude Desktop** — Settings → Developer → Edit Config → paste into `claude_desktop_config.json`, then restart.
- **Claude Code** —
  ```bash
  claude mcp add blackwall -e BLACKWALL_API_KEY=bw_live_your_key_here -- npx -y blackwall-mcp
  ```
- **Windsurf** — add the same `mcpServers` config (Settings → Cascade → MCP, or its `mcp_config.json`).
- **Google Antigravity** — agent panel → Manage MCP Servers → View raw config → paste into `mcp_config.json`. Full guide: [`../antigravity`](../antigravity).
- **Any other host / local test** —
  ```bash
  BLACKWALL_API_KEY=bw_live_your_key_here npx -y blackwall-mcp
  ```

## 3. Tell the agent to use it
Add to your agent's rules / system prompt:

> Before any irreversible action — deleting files, running destructive SQL or shell
> commands, force-pushing, making payments — call the `forecast` tool first and stop
> if it returns STOP.

As an MCP tool, `forecast` is called at the agent's discretion, so this rule is what
makes it reliable.

## Try it with zero risk — observe mode
Add `"BLACKWALL_MODE": "observe"` to the `env`. It scores and logs every action but
**never blocks** — your agent behaves exactly as it does today. Review your dashboard
after a week to see what it *would* have caught, then switch to `enforce` (the default).

## Reference
- Package + full `forecast` tool docs: [`blackwall-mcp`](https://www.npmjs.com/package/blackwall-mcp)
- Site & keys: https://blackwalltier.com
