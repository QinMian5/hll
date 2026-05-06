---
abstract: Repository-level MCP service overview for public search access and integration boundaries.
out_of_scope: Browser session flows, Logto tenant provisioning, and client-specific setup walkthroughs.
---

# HLL MCP Integration Notes

`apps/mcp` runs the public remote MCP service for Humanity's Last Library. It is
the public programmatic access boundary for agent clients.

## Endpoint

The MCP service exposes a Streamable HTTP MCP endpoint at:

```text
/mcp
```

In local development, `make dev-up` exposes it at:

```text
http://localhost:8002/mcp
```

Production deployments expose the endpoint through the public web host. The
[web app docs route](https://knowledge.orbitalis.org/docs) is the end-user setup
surface for supported MCP clients.

## Tool Surface

The first public MCP tool is:

```text
search
```

The `search` tool accepts a non-empty query. Use concise keyword-style queries:
prefer key terms, entity names, domain concepts, or short noun phrases instead
of full sentence questions or broad instructions.

The tool returns:

- matched results with `title` and `content`
- connected titles for nearby context

The MCP service delegates search execution to the private API through generated
internal contract artifacts. It does not import private API internals or access
knowledge graph tables directly.

## Authentication

MCP clients authenticate with:

```http
Authorization: Bearer <Logto personal access token>
```

The service exchanges the presented personal access token through Logto,
validates the resulting access token, enforces account-level quota, and computes
a server-secret PAT fingerprint for attribution. Raw personal access tokens must
not be stored in logs, Redis, PostgreSQL, or response payloads.

## Usage And Analytics

The MCP service records usage events for successful tool calls,
quota-rejected calls, and backend search errors after quota is reserved.
Successful `search` calls also create agent-search analytics records.

These records are a current capability, but the optimization loop is still a
future direction. The intent is to use aggregate agent search behavior to improve
retrieval, knowledge structure, and maintenance priorities over time.

## Boundaries

- MCP owns protocol handling, public token authentication, quota, usage
  attribution, and MCP-only analytics.
- The private API owns search semantics and the authoritative OpenAPI contract.
- The web BFF owns browser sessions, Dashboard token management, and browser
  data endpoints.
- The web app docs route owns client-specific setup guidance for end users.
