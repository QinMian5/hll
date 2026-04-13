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
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006.

## Selection Principles
- Prefer mature defaults with low integration risk.
- Keep phase-1 operational complexity minimal.
- Keep contract-driven integration (`OpenAPI -> generated client`).
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

### Frontend
- Workspace/package manager: root `pnpm` workspace
- Build tool: `Vite`
- UI framework: `React` + `TypeScript`
- Graph rendering engines: `React Flow` for branch taxonomy browsing and `deck.gl` for leaf relation rendering
- Layout engine: `d3-force`
- Server-state management: `TanStack Query`
- Contract consumption: generated TypeScript client from repository OpenAPI artifacts
- Styling: `Tailwind CSS`
- Component baseline: `shadcn/ui`
- Tooling: `Biome`, `TypeScript`, `Commitlint`

#### Why selected
- Fast iteration and low boilerplate.
- Strong compatibility with generated OpenAPI client.
- `React Flow` keeps the branch drill-down surface simple for lower-count bubble navigation.
- `deck.gl` provides GPU-backed rendering for dense leaf point, edge, and card visualization under the same frontend-owned layout model.
- `d3-force` keeps branch and leaf geometry frontend-owned and deterministic without pushing coordinates into backend contracts.
- No dependency on semantic-map tile/snapshot rendering stack.
- Layout remains frontend-owned, so backend contracts stay semantic and avoid coordinate persistence coupling.

### Infrastructure
- Containerization: `Docker`
- Local orchestration: `Docker Compose`
- Primary datastore: `PostgreSQL`
- Queue broker: `Redis` via project-managed container image `redis:7-bookworm`
- Runtime external integration: OpenAI Embeddings API with model `text-embedding-3-small`

## Installed but Deferred for Runtime Use
- `TanStack Router`
- `Zustand`
- `TanStack Form`
- `Zod`
- `Logto`

## Explicit Non-Goals for Phase-1
- Semantic-map snapshot/tile architecture.
- Authentication/authorization flows.
- Cache runtime dependency.
- Keyword or hybrid retrieval runtime dependency.
- Additional backend service decomposition.
