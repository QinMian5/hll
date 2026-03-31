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
- Defer non-essential runtime components even if dependencies are preinstalled.

## Selected Stack (Phase-1)

### Backend
- Package and environment manager: `uv`
- Language and runtime: `Python` + `Uvicorn`
- Web framework: `FastAPI`
- Data validation and settings: `Pydantic v2` + `pydantic-settings`
- ORM and migrations: `SQLAlchemy 2` + `Alembic`
- Database: `PostgreSQL`
- Vector extension: `pgvector`

#### Why selected
- The stack is aligned with API-first development and deterministic contract export.
- It provides a stable path for `Node/Edge/Adjacency` relational modeling and `Node.embedding` vector storage.
- Tooling is modern and compatible with monorepo governance and reproducible local/CI workflows.

### Frontend
- Workspace and package manager: `pnpm`
- Build tool: `Vite`
- UI framework: `React` + `TypeScript`
- Server-state management: `TanStack Query`
- Styling: `Tailwind CSS`
- Component library baseline: `shadcn/ui`

#### Why selected
- Fast development loop and low initial boilerplate.
- Strong compatibility with generated TypeScript API client consumption.
- Sufficient for phase-1 graph browsing and read-oriented UI.

### Infrastructure
- Containerization: `Docker`
- Local orchestration: `Docker Compose`
- Primary datastore: `PostgreSQL` (containerized for local/CI parity)

#### Why selected
- Minimal reproducible infrastructure baseline.
- Low operational overhead for a single API service and single web client.

## Installed but Deferred for Runtime Use
- `Redis`
- `TanStack Router`
- `Zustand`
- `TanStack Form`
- `Zod`
- `Logto`

### Decision rule
- Dependencies may be preinstalled in phase-1 to reduce later setup friction.
- Deferred components are not required in the phase-1 runtime path unless a scope decision changes.

## Why Deferred Instead of Enabled in Phase-1
- `Redis`: cache layer is reserved and not part of phase-1 runtime.
- `TanStack Router`: route complexity is not yet high enough to require type-safe router specialization.
- `Zustand`: global client-state complexity is not yet justified.
- `TanStack Form` and `Zod`: phase-1 is read-first and does not require advanced form workflows.
- `Logto`: authentication and access-control are explicitly out of current phase scope.

## Explicit Non-Goals for Phase-1
- Enabling authentication/authorization flows.
- Introducing cache runtime dependency.
- Building complex form or admin-console interaction systems.
- Adding additional backend service decomposition.

## Revisit Triggers
- Introduce `Redis` when measurable read hot paths require cache-level latency reduction.
- Enable `TanStack Router` when URL/stateful navigation becomes a core behavior surface.
- Enable `Zustand` when cross-feature client state cannot be managed cleanly with local state/query cache.
- Enable `TanStack Form`/`Zod` when write-heavy workflows enter scope.
- Enable `Logto` when identity and access control move into active requirements.
