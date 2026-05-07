---
abstract: Developer guide for local setup, root commands, contracts, and verification.
out_of_scope: Production operations, product positioning, and MCP client setup walkthroughs.
---

# Development Guide

This repository is governed from the root with `Makefile`, `scripts/`, a Python
`uv` workspace, and a `pnpm` workspace.

## Prerequisites

- Docker and Docker Compose for local services.
- `uv` for Python workspace commands.
- `pnpm` for frontend and contract-generation packages.

## Root Commands

```bash
make bootstrap
```

Installs and synchronizes local dependencies and tooling.

```bash
make dev-up
make dev-down
```

`make dev-up` resets development API data from the bootstrap snapshot, then
starts the local development stack. `make dev-down` stops the development stack.
Development uses Docker Compose and repository-owned environment files under
`infra/env/`.

```bash
make test
make check
make integration
```

Runs the default fast test suite, the pre-submit aggregate checks, or the heavier
integration flow.

```bash
make alembic-upgrade-dev
make alembic-upgrade-test
make alembic-upgrade-prod
```

Applies app migrations to the selected environment.

## Contracts

The private API contract is exported as OpenAPI and projected into generated
client artifacts under `packages/contracts`.

```bash
bash scripts/contracts.sh
bash scripts/contracts-check.sh
```

Run `bash scripts/contracts.sh` after changing API response shapes or request
contracts. Run `bash scripts/contracts-check.sh` before submitting changes that
depend on generated client artifacts. The root `make check` command includes the
contract verification step.

## Frontend Commands

```bash
pnpm run js:lint
pnpm run js:typecheck
pnpm run web:test
pnpm run web:build
```

The web app lives under `apps/web` and uses React, TypeScript, Vite, Express,
TanStack Router, and generated OpenAPI clients through the BFF boundary.

## Backend Commands

Python services are workspace members under `apps/`. Use root `make` commands
for normal repository workflows. For targeted service work, run `uv` in the
relevant workspace member.

```bash
uv run --project apps/api pytest
uv run --project apps/mcp pytest
uv run --project apps/source_pipeline pytest
```

Prefer targeted tests while developing, then run the root verification command
that matches the change's blast radius.

## Runtime Surfaces

After `make dev-up` refreshes development API data and starts the local stack,
the development environment exposes the web app, private services, databases,
Redis-backed state, and the public MCP development endpoint. The MCP development
endpoint is:

```text
http://localhost:8002/mcp
```

Client setup walkthroughs live in [MCP client setup](mcp.md).
