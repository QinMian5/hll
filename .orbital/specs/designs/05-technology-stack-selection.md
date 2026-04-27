---
abstract: Technology stack selection for MVP phase-1 with speed-first delivery and extensible architecture boundaries.
out_of_scope: Detailed implementation wiring, benchmark-driven tuning, and phase-2+ capability rollout plans.
---

# Design: 05-technology-stack-selection

## Active Truth Policy
- This document defines only currently accepted stack decisions for MVP phase-1.
- Superseded choices are removed instead of preserved as transition history.

## Context
- Purpose: select a modern stack that maximizes delivery speed while preserving long-term extensibility.
- Scope/Boundaries: backend stack, frontend stack, infrastructure stack, and phase-1 defer decisions.
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Selection Principles
- Prefer mature defaults with low integration risk.
- Keep phase-1 operational complexity minimal.
- Keep contract-driven internal backend integration (`OpenAPI -> generated client`).
- Defer non-essential runtime components.

## Selected Stack (Phase-1)

### Backend
- Package and environment manager: root `uv` workspace with member `pyproject.toml` files
- Language and runtime: `Python` + `Uvicorn`
- Web framework: `FastAPI`
- Data validation and settings: `Pydantic v2` + `pydantic-settings`
- ORM and migrations: `SQLAlchemy 2` + `Alembic`
- Database: `PostgreSQL`
- Vector extension: `pgvector`
- Async worker framework: `Dramatiq`
- External job-queue integration: upstream `job-queue-mcp-client` Python SDK for producer/result-reader calls and machine-to-machine token acquisition

#### Why selected
- Aligned with API-first development and deterministic contract export.
- Stable path for `Node/Edge/Adjacency` modeling and `Node.embedding` vector storage.
- Root `uv.lock` and member-local declarations provide reproducible Python workflows.

### Operator CLI
- Package and environment manager: root `uv` workspace with `apps/cli` as member
- Language and runtime: `Python`
- Agent framework: `Pydantic AI`
- Agent workflow graph: `Pydantic Graph`
- Validation/settings: `Pydantic v2` + `pydantic-settings`
- HTTP client: `httpx`

### MCP Server
- Package and environment manager: root `uv` workspace with `apps/mcp` as member
- Language and runtime: `Python` + `Uvicorn`
- MCP framework: official Model Context Protocol Python SDK
- Transport: Streamable HTTP
- Data validation and settings: `Pydantic v2` + `pydantic-settings`
- HTTP client: `httpx`
- Public identity authority: Logto personal access token exchange plus Logto-issued access-token validation
- Quota and token-exchange cache: Redis-backed MCP-owned state
- Durable usage ledger: PostgreSQL through SQLAlchemy 2 and app-local Alembic assets owned by `apps/mcp`
- Internal backend contract consumption: generated internal Python client under `packages/contracts/generated/python/` derived from repository OpenAPI artifacts

#### Why selected
- Matches the accepted public programmatic access boundary without mixing MCP protocol handling into browser BFF session flows or private FastAPI route ownership.
- Keeps the first MCP tool aligned with the existing private search contract through generated internal client artifacts.
- Uses the project-owned Logto authority for user-created personal access tokens while preserving short-lived access-token validation for resource authorization.

### Frontend
- Workspace/package manager: root `pnpm` workspace
- Build tool: `Vite`
- Web server/BFF runtime: `Node.js` + `Express`
- UI framework: `React` + `TypeScript`
- Client routing: `TanStack Router`
- Graph rendering engines: `React Flow` for branch taxonomy browsing and `deck.gl` for leaf relation rendering
- Layout engine: `d3-force`
- Server-state management: `TanStack Query`
- Internal backend contract consumption: generated TypeScript client from repository OpenAPI artifacts, used by the web BFF
- Styling: `Tailwind CSS`
- Component baseline: `shadcn/ui`
- Web identity provider: `Logto`
- Web session and quota state: Redis-backed server-side state with secure browser cookies
- Tooling: `Biome`, `TypeScript`, `Commitlint`

#### Why selected
- Fast iteration and low boilerplate.
- Strong compatibility with generated OpenAPI client.
- Express keeps the web runtime close to the existing Vite/React app while adding a server-owned BFF boundary for session, quota, and internal API calls.
- `React Flow` keeps the branch drill-down surface simple for lower-count bubble navigation.
- `deck.gl` provides GPU-backed rendering for dense leaf point, edge, and card visualization under the same frontend-owned layout model.
- `d3-force` keeps branch and leaf geometry frontend-owned and deterministic without pushing coordinates into backend contracts.
- No dependency on semantic-map tile/snapshot rendering stack.
- Layout remains frontend-owned, so backend contracts stay semantic and avoid coordinate persistence coupling.
- Logto provides the accepted web identity authority while the BFF keeps access tokens out of browser runtime state.

### Infrastructure
- Containerization: `Docker`
- Local orchestration: `Docker Compose`
- Primary datastore: `PostgreSQL`
- Queue broker, web session store, and web quota counter store: `Redis` via project-managed container image `redis:7-bookworm`
- Runtime external integration: OpenAI Embeddings API with model `text-embedding-3-small`

## Installed but Deferred for Runtime Use
- `Zustand`
- `TanStack Form`
- `Zod`

## Explicit Non-Goals for Phase-1
- Semantic-map snapshot/tile architecture.
- General-purpose result cache or business-object cache runtime dependency.
- Keyword or hybrid retrieval runtime dependency.
- Additional backend service decomposition.
- Public REST API access for external users or external programmatic clients.
