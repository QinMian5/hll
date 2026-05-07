---
abstract: End-user MCP client setup guide for connecting Codex, Claude Code, and OpenClaw to Humanity's Last Library.
out_of_scope: MCP service implementation, private API boundaries, Logto tenant provisioning, and local service development.
---

# HLL MCP Client Setup

Humanity's Last Library exposes a public remote MCP endpoint that agent clients
can use to search the knowledge network.

Use the production endpoint:

```text
https://knowledge.orbitalis.org/mcp
```

## Prepare A Dashboard Token

Create a personal access token before configuring a client:

```text
Dashboard > Tokens > Create Token > Copy token
```

Use the copied token wherever the examples below show:

```text
<Dashboard PAT>
```

## Codex

Add HLL as a Streamable HTTP MCP server:

```bash
codex mcp add hll --url https://knowledge.orbitalis.org/mcp
```

Add the Dashboard token to the Codex server entry in `~/.codex/config.toml`:

```toml
[mcp_servers.hll]
url = "https://knowledge.orbitalis.org/mcp"
http_headers = { Authorization = "Bearer <Dashboard PAT>" }
```

Inspect the saved server:

```bash
codex mcp get hll
```

Confirm HLL appears in the configured MCP server list:

```bash
codex mcp list
```

## Claude Code

Add HLL with HTTP transport and bearer authentication:

```bash
claude mcp add --transport http hll https://knowledge.orbitalis.org/mcp --header "Authorization: Bearer <Dashboard PAT>"
```

Inspect the saved server:

```bash
claude mcp get hll
```

Confirm HLL appears in Claude Code's MCP server list:

```bash
claude mcp list
```

## OpenClaw

Save HLL as a Streamable HTTP MCP server with the Dashboard token header:

```bash
openclaw mcp set hll '{"url":"https://knowledge.orbitalis.org/mcp","transport":"streamable-http","headers":{"Authorization":"Bearer <Dashboard PAT>"}}'
```

Inspect the saved server:

```bash
openclaw mcp show hll --json
```

Confirm HLL appears in the OpenClaw MCP registry:

```bash
openclaw mcp list
```

## Notes

- Keep Dashboard tokens private. Do not commit them to source control or paste
  them into shared logs.
- The current public MCP tool is `search`.
- Prefer concise keyword-style search queries: entity names, domain concepts,
  or short noun phrases work better than broad instructions.
- The same setup guidance is available in the web product docs at
  [knowledge.orbitalis.org/docs](https://knowledge.orbitalis.org/docs).
