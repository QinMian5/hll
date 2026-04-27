---
abstract: Canonical MVP repository layout and directory ownership boundaries for the full-stack monorepo.
out_of_scope: Domain behavior semantics, detailed error taxonomy, and advanced CI pipeline design.
---

# Design: 04-repository-structure

## Active Truth Policy
- This document contains only currently accepted repository-layout decisions.
- Superseded layout rules are removed instead of preserved as transition history.

## Context
- Purpose: define canonical monorepo layout and directory ownership for MVP.
- Scope/Boundaries: top-level topology, application/package placement, and path-level ownership boundaries.
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Repository Topology
```text
repo/
  apps/
    api/
    cli/
    knowledge_corpus/
    source_pipeline/
    web/
  packages/
    contracts/
  infra/
  scripts/
  human_workspace/
  .orbital/specs/
  Makefile
  package.json
  pnpm-workspace.yaml
  pyproject.toml
  uv.lock
```

## Directory Ownership
- `apps/api`: FastAPI source, API tests, and Alembic assets.
- `apps/cli`: local operator-facing CLI source.
- `apps/knowledge_corpus`: local/offline corpus app source and app-local DB lifecycle assets.
- `apps/source_pipeline`: project-owned source-processing runtime, queue orchestration, and pipeline state.
- `apps/web`: React web client source, Express BFF server, public web API endpoints, server-side web session handling, and web access-control state.
- `packages/contracts`: OpenAPI snapshot, generated clients/types, contracts scripts.
- `infra`: deployment/environment templates.
- `scripts`: repository automation scripts.
- `human_workspace`: human-operated research and offline workflow scripts.
- `.orbital/specs`: active requirements/design/plan documents.

## API Application Layout (`apps/api`)
```text
apps/api/
  alembic/
    env.py
    versions/
  src/
    core/
    entrypoints/
      runtime.py
      api/
      worker/
    modules/
      knowledge_graph/
      taxonomy/
      taxonomy_classification/
      search/
      ingestion/
    shared/
      db/
      integrations/
      utils/
  tests/
```

## API Module Content Ownership
- `modules/knowledge_graph`: graph persistence truth (`model.py`, `repo.py`, `service.py`, `dto.py`, `ports.py`, `builders.py`).
- `modules/taxonomy`: taxonomy persistence ownership, import orchestration, taxonomy view API contracts and service/repo logic.
- `modules/taxonomy_classification`: operator-triggered classification job submission, job-queue result consumption, webhook/reconcile state, and assignment-move orchestration.
- `modules/search`: read-side HTTP contract and read orchestration.
- `modules/ingestion`: write-side HTTP contract/orchestration, queue adapter, and worker job-processing primitives.
- `entrypoints`: composition and process bootstrap layer.

## Web Application Layout (`apps/web`)
```text
apps/web/
  server/
    auth/
    internal-api/
    rate-limit/
    routes/
  src/
    app/
    features/
      taxonomy-view/
      knowledge/
      search/
    shared/
      ui/
      hooks/
      utils/
      config/
  tests/
```

## Operator CLI Layout (`apps/cli`)
```text
apps/cli/
  main.py
```

## Knowledge Corpus Layout (`apps/knowledge_corpus`)
```text
apps/knowledge_corpus/
  alembic/
  src/
    knowledge_corpus/
      config.py
      db/
      wikipedia/
  tests/
```

## Source Pipeline Layout (`apps/source_pipeline`)
```text
apps/source_pipeline/
  alembic/
  src/
    source_pipeline/
      config.py
      db/
      entrypoints/
        orchestrator.py
        webhook_receiver.py
      pipeline_intake/
      pipeline_runtime/
      pipeline_webhook/
      page_to_card/
      card_review/
      card_repair/
      pipeline_handoff/
  tests/
```

## Contracts Package Layout (`packages/contracts`)
```text
packages/contracts/
  openapi/
    openapi.json
  generated/
    types.ts
    client.ts
  scripts/
```

## Contract Integration
- Backend exports OpenAPI to `packages/contracts/openapi/openapi.json`.
- Generated artifacts under `packages/contracts/generated` are versioned.
- Repository-owned code that calls internal backend APIs consumes those APIs only through generated contract artifacts.
- Browser-side web code consumes public web API endpoints owned by `apps/web` and does not call internal backend APIs directly.
- Owned `packages/` content is limited to repository-owned contract artifacts. Upstream client SDKs are consumed as external package dependencies by the app members that use them.

## Boundary Rules
1. Repository-root configuration files own cross-member tooling/workspace behavior.
2. Member directories retain only member-scoped dependencies/runtime config/source assets.
3. `packages/contracts` must not contain application business logic.
4. `infra` must not contain application business logic.
5. `apps/api/src/shared` contains reusable technical capabilities only.
6. Runtime configuration source is `.env` through `pydantic-settings`; YAML is not runtime config.
7. `apps/api/src/modules/knowledge_graph` remains sole owner of graph persistence models/repositories.
8. `apps/api/src/modules/search`, `apps/api/src/modules/ingestion`, and `apps/api/src/modules/taxonomy` access graph truth through service ports only.
9. `apps/api/src/modules/taxonomy` owns taxonomy persistence plus taxonomy view API contracts.
10. `apps/api/src/modules/taxonomy_classification` owns job-queue-backed classification orchestration and does not own graph/taxonomy persistence projections.
11. `apps/api/src/modules/**` must not import `apps/api/src/entrypoints/**`.
12. `apps/cli` owns local review/submission flow and must not own backend persistence/runtime concerns.
13. `human_workspace` assets are not authoritative online API/runtime contracts.
14. `apps/knowledge_corpus` is isolated local/offline ownership and not imported by online apps.
15. `apps/source_pipeline` owns project-level source-processing runtime and remains source-agnostic within this repository boundary.
16. `apps/source_pipeline` must not import `apps/api/src/entrypoints/**`.
17. `apps/source_pipeline` interacts with the online knowledge system only through accepted HTTP contracts and must not import `apps/api/src/modules/ingestion/**`, `apps/api/src/modules/knowledge_graph/**`, or write knowledge database tables directly.
18. `apps/web` owns public web HTTP endpoints and must not import `apps/api/src/**`; it interacts with `apps/api` through the generated internal API client over Docker-network HTTP.

## Governance Anchors
- Architecture constraints: `03-architecture-constraints`.
- Minimal quality gates: lint/format, typecheck, test, contract drift.
- Dependency-direction enforcement: `import-linter` contracts in `apps/api/pyproject.toml`.
