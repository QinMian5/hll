---
abstract: Canonical MVP repository layout and directory ownership boundaries for the full-stack monorepo.
out_of_scope: Domain behavior semantics, detailed error taxonomy, and advanced CI pipeline design.
---

# Design: 04-repository-structure

## Active Truth Policy
- This document contains only currently accepted repository-layout decisions.
- Superseded layout rules are removed instead of kept as transition history.
- This document defines layout ownership, not detailed architecture constraints.

## Context
- Purpose: define the canonical monorepo layout and directory ownership for the MVP phase.
- Scope/Boundaries: covers top-level repository topology, application/package placement, and path-level ownership boundaries.
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006.

## Repository Topology
```text
repo/
  apps/
    api/
    cli/
    web/
  packages/
    contracts/
  infra/
  scripts/
  .orbital/specs/
  Makefile
  README.md
```

## Directory Ownership
- `apps/api`: FastAPI service source, runtime entrypoint, API-side tests, and Alembic migration assets.
- `apps/cli`: Local operator-facing CLI source, local agent review flow, submission adapter, and CLI-side tests.
- `apps/web`: React web client source and web-side tests.
- `packages/contracts`: authoritative OpenAPI snapshot and generated client artifacts for frontend consumption.
- `infra`: deployment and environment template assets, not application business logic.
- `scripts`: repository automation scripts invoked by top-level governance commands.
- `.orbital/specs`: active requirements and design documents.

## Application Layout
### API Application (`apps/api`)
```text
apps/api/
  alembic/
    env.py
    versions/
  alembic.ini
  src/
    main.py
    core/
      config.py
      logging.py
      errors.py
    entrypoints/
      runtime.py
      api/
        app.py
        providers.py
      worker/
        actors.py
    modules/
      knowledge_graph/
      search/
      ingestion/
      semantic_map/
    shared/
      db/
      integrations/
      utils/
  tests/
  pyproject.toml
  Dockerfile
```
- `apps/api/src/core/config.py` is the single `pydantic-settings` entrypoint.

### API Module Content Ownership
- `modules/knowledge_graph` contains domain truth and persistence ownership (`model.py`, `repo.py`, `service.py`, `dto.py`, `ports.py`, `builders.py`).
- `modules/knowledge_graph` excludes HTTP endpoint files and queue transport wiring.
- `modules/search` contains read-side HTTP contract files (`api.py`, `schema.py`) and read orchestration service logic.
- `modules/search` excludes direct persistence access and worker/queue concerns.
- `modules/ingestion` contains write-side HTTP contract files (`api.py`, `schema.py`), ingestion orchestration (`service.py`), ingestion-owned queue broker (`queue.py`), and worker job-processing primitives (`workers.py`).
- `modules/ingestion` excludes graph persistence models/repositories and search-response orchestration.
- `modules/semantic_map` contains semantic-map HTTP read contract files (`api.py`, `schema.py`), snapshot read/rebuild orchestration, and semantic-map DTO/port contracts.
- `modules/semantic_map` excludes graph persistence models/repositories, search-query orchestration, and frontend rendering implementation.
- `entrypoints` is the composition layer and contains FastAPI app/provider wiring and Dramatiq actor registration.

### Web Application (`apps/web`)
```text
apps/web/
  src/
    app/
    features/
      semantic-map/
      knowledge/
      search/
    shared/
      ui/
      hooks/
      utils/
      config/
  tests/
  package.json
  Dockerfile
```

### Operator CLI Application (`apps/cli`)
```text
apps/cli/
  src/
    main.py
    card_review_cli/
      config.py
      models.py
      review_agent.py
      graph.py
      submitter.py
      formatter.py
  tests/
  pyproject.toml
```
- `apps/cli` owns the local single-card submission command, typed review output models, local agent orchestration, graph branching, backend submission adapter, and CLI-side tests.
- `apps/cli` excludes knowledge-graph persistence ownership, backend ingestion internals, and frontend rendering concerns.

### Contracts Package (`packages/contracts`)
```text
packages/contracts/
  openapi/
    openapi.json
  generated/
    types.ts
    client.ts
  scripts/
  package.json
  README.md
```

## Contract Integration
- Backend exports OpenAPI into `packages/contracts/openapi/openapi.json`.
- Generated artifacts in `packages/contracts/generated` are versioned in repository.
- Frontend consumes backend APIs only through generated contract artifacts.

## Boundary Rules
1. `packages/contracts` SHALL NOT contain application business logic.
2. `infra` SHALL NOT contain application business logic.
3. `apps/api/src/shared` SHALL contain reusable technical capabilities only.
4. Runtime configuration is sourced from `.env` through `pydantic-settings`; YAML is not a runtime configuration source.
5. `infra/env` contains environment templates and active env files consumed by runtime and test `Settings`.
6. `apps/api/src/modules/knowledge_graph` SHALL remain the only owner of graph persistence models and repositories.
7. `apps/api/src/modules/search`, `apps/api/src/modules/ingestion`, and `apps/api/src/modules/semantic_map` SHALL access graph persistence only through `knowledge_graph` domain service ports.
8. `apps/api/src/modules/knowledge_graph` SHALL include `model.py`, `repo.py`, `service.py`, domain DTOs, and domain service ports.
9. `apps/api/src/modules/knowledge_graph` SHALL NOT include HTTP route files, queue broker setup, or worker actor definitions.
10. `apps/api/src/modules/search` SHALL include only read-side API transport and orchestration logic.
11. `apps/api/src/modules/search` SHALL NOT import `modules/knowledge_graph/model.py` or `modules/knowledge_graph/repo.py`.
12. `apps/api/src/modules/ingestion` SHALL include write-side API transport/orchestration plus ingestion-owned queue broker and worker job-processing primitives.
13. `apps/api/src/modules/ingestion` SHALL NOT import `modules/knowledge_graph/model.py` or `modules/knowledge_graph/repo.py`.
14. `apps/api/src/shared` SHALL include only cross-module infrastructure (`db`, external integrations, and generic utilities); ingestion-specific queue code SHALL NOT be placed under `shared`.
15. `apps/api/src/entrypoints/runtime.py` SHALL be the runtime composition root for app/worker settings and singleton dependency assembly.
16. Runtime modules under `apps/api/src/**` SHALL NOT read environment variables directly (`os.getenv`, `os.environ`).
17. Runtime dependency resolution SHALL use explicit injection and SHALL NOT use nullable-fallback dependency signatures.
18. `apps/api/src/modules/**` SHALL NOT import `apps/api/src/entrypoints/**`.
19. `apps/api/src/modules/semantic_map` SHALL access knowledge-domain truth only through `knowledge_graph` service ports and SHALL NOT import `modules/knowledge_graph/model.py` or `modules/knowledge_graph/repo.py`.
20. `apps/web/src/features/semantic-map` SHALL own semantic-map deck.gl rendering, semantic-map API adapters, and feature-specific UI overlays; only genuinely reusable technical primitives may move into `apps/web/src/shared/**`.
21. `apps/cli` SHALL own only local command execution, agent review orchestration, and ingestion API submission behavior.
22. `apps/cli` SHALL NOT own backend persistence, worker runtime, or direct database access.

## Governance Anchors
- Detailed architecture constraints are defined in `03-architecture-constraints`.
- Minimal phase-1 quality gates are `lint/format`, `typecheck`, `test`, and `contract drift`.
- Dependency-direction enforcement is implemented through `import-linter` contracts in `apps/api/pyproject.toml`.
- This document defines layout ownership only and does not redefine dependency policy details.

## Deferred to Later Phases
- Detailed CI stage matrices and environment-specific gate variants.
- Full import-matrix automation and advanced architecture lint policies.
