---
abstract: Technology stack selection for MVP phase-1 with speed-first delivery and extensible architecture boundaries.
out_of_scope: Detailed implementation wiring, benchmark-driven tuning, and phase-2+ capability rollout plans.
---

# Design: 05-technology-stack-selection

## Active Truth Policy
- This document defines only currently accepted stack decisions for MVP phase-1.
- Superseded choices are removed instead of described as transition history.
- This document records selection rationale, not implementation playbooks.

## Context
- Purpose: select a modern stack that maximizes delivery speed while preserving architecture extensibility.
- Scope/Boundaries: backend stack, frontend stack, infrastructure stack, and phase-1 defer decisions.
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006.

## Selection Principles
- Prefer mature defaults with low integration risk.
- Keep phase-1 operational complexity minimal.
- Keep strong contract-driven integration (`OpenAPI -> generated client`).
- Defer non-essential runtime components except approved ingestion async dependencies.

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
- Projection/clustering baseline: `scikit-learn`

#### Why selected
- The stack is aligned with API-first development and deterministic contract export.
- It provides a stable path for `Node/Edge/Adjacency` relational modeling and `Node.embedding` vector storage.
- `scikit-learn` provides the approved deterministic Phase 1 PCA + agglomerative-clustering rebuild baseline without introducing a second backend service.
- Root `uv.lock`, root `.venv`, and member-local dependency declarations provide reproducible Python workflows without per-member virtual environments.

### Operator CLI
- Package and environment manager: root `uv` workspace with `apps/cli` as a member
- Language and runtime: `Python`
- Agent framework: `Pydantic AI`
- Agent workflow graph: `Pydantic Graph`
- Validation and settings: `Pydantic v2` + `pydantic-settings`
- HTTP client: `httpx`

#### Why selected
- The stack keeps the review workflow agent-first while preserving typed structured outputs.
- `Pydantic AI` aligns with the requirement that review judgment comes from an LLM agent rather than rule-coded heuristics.
- `Pydantic Graph` provides an explicit and testable approval vs. submission branching model without coupling the CLI to backend runtime internals.
- `httpx` keeps the CLI submission boundary simple and compatible with the authoritative ingestion API contract.

### Frontend
- Workspace and package manager: root `pnpm` workspace
- Build tool: `Vite`
- UI framework: `React` + `TypeScript`
- Semantic-map rendering engine: `deck.gl`
- Server-state management: `TanStack Query`
- Contract consumption: generated TypeScript client from repository OpenAPI artifacts
- Styling: `Tailwind CSS`
- Component library baseline: `shadcn/ui`
- Repository-level JS/TS developer tooling: `Biome`, `TypeScript`, `Commitlint`
- Root `pnpm` commands are scoped to JS/TS responsibilities rather than full-repository orchestration

#### Why selected
- Fast development loop and low initial boilerplate.
- Strong compatibility with generated TypeScript API client consumption.
- `deck.gl` supports non-geospatial 2D semantic-map rendering, viewport-driven tile loading, and semantic zoom.
- Sufficient for phase-1 semantic-map browsing and read-oriented UI.
- Root-managed JS/TS tooling keeps cross-member quality rules aligned across `apps/web` and `packages/contracts`.
- Repository-level orchestration remains in a small human-facing `Makefile`, which avoids overloading `pnpm` with Python-facing workflows.

### Infrastructure
- Containerization: `Docker`
- Local orchestration: `Docker Compose`
- Primary datastore: `PostgreSQL` (containerized for local/CI parity)
- Queue broker: `Redis` via project-managed container image `redis:7-bookworm`
- Runtime external integration: OpenAI Embeddings API with model `text-embedding-3-small`

#### Why selected
- Minimal reproducible infrastructure baseline.
- Low operational overhead for a single API service and single web client.
- Queue transport remains internal to Docker backend network and does not require host-local Redis.

## Installed but Deferred for Runtime Use
- `TanStack Router`
- `Zustand`
- `TanStack Form`
- `Zod`
- `Logto`

### Decision rule
- Dependencies may be preinstalled in phase-1 to reduce later setup friction.
- Deferred components are not required in the phase-1 runtime path unless a scope decision changes.

## Why Deferred Instead of Enabled in Phase-1
- `TanStack Router`: route complexity is not yet high enough to require type-safe router specialization.
- `Zustand`: global client-state complexity is not yet justified.
- `TanStack Form` and `Zod`: phase-1 is read-first and does not require advanced form workflows.
- `Logto`: authentication and access-control are explicitly out of current phase scope.

## Explicit Non-Goals for Phase-1
- Enabling authentication/authorization flows.
- Introducing cache runtime dependency.
- Introducing keyword or hybrid retrieval runtime dependency.
- Building complex form or admin-console interaction systems.
- Adding additional backend service decomposition.

## Revisit Triggers
- Introduce Redis cache usage when measurable read hot paths require cache-level latency reduction.
- Enable `TanStack Router` when URL/stateful navigation becomes a core behavior surface.
- Enable `Zustand` when cross-feature client state cannot be managed cleanly with local state/query cache.
- Enable `TanStack Form`/`Zod` when write-heavy workflows enter scope.
- Enable `Logto` when identity and access control move into active requirements.
