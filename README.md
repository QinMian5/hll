# Knowledge Monorepo

This repository is governed from the root with `Makefile` and `scripts/`.

## Root Commands

- `make bootstrap`: install and sync dependencies.
- `make dev-up`: reset development API data from the bootstrap snapshot and start the Docker Compose dev stack.
- `make dev-down`: stop development runtime.
- `make contracts`: export and generate API contracts.
- `make contracts-check`: verify contract artifacts are up to date.
- `make test`: run backend and frontend tests.
- `make check`: run contract verification and tests.

## Public MCP

`apps/mcp` runs the public remote MCP service. It exposes `/mcp` and currently
registers one tool, `search`. MCP clients authenticate with
`Authorization: Bearer <Logto personal access token>`; the service exchanges the
PAT through Logto, enforces user-level and PAT-level quota in Redis, calls the
private search API through the generated Python contract client, and records MCP
usage in a dedicated MCP PostgreSQL database through `apps/mcp` Alembic
migrations.

In development, `make dev-up` exposes the MCP service at `http://localhost:8002/mcp`.
