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
    mcp/
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
- `apps/mcp`: public MCP server source, MCP tests, app-local Alembic assets, PAT-backed programmatic access control, quota and usage attribution, MCP-owned usage-table access, and generated internal search API consumption.
- `apps/source_pipeline`: project-owned source-processing runtime, queue orchestration, and pipeline state.
- `apps/web`: React web client source, Express BFF server, public web API endpoints, server-side web session handling, web access-control state, and authenticated dashboard token-management orchestration.
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
    dashboard/
    internal-api/
    rate-limit/
    routes/
  src/
    app/
    features/
      dashboard/
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

## MCP Application Layout (`apps/mcp`)
```text
apps/mcp/
  alembic/
  src/
    knowledge_mcp/
      auth/
      internal_api/
      quota/
      usage/
      server.py
      config.py
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
    python/
  scripts/
```

## Contract Integration
- Backend exports OpenAPI to `packages/contracts/openapi/openapi.json`.
- Generated artifacts under `packages/contracts/generated` are versioned for repository-owned internal API consumers.
- Repository-owned code that calls internal backend APIs consumes those APIs only through generated contract artifacts.
- Browser-side web code consumes public web API endpoints owned by `apps/web` and does not call internal backend APIs directly.
- MCP service code consumes the private search API through generated Python internal API client artifacts under `packages/contracts/generated/python/` and does not call private FastAPI routes through ad hoc HTTP code.
- Owned `packages/` content is limited to repository-owned contract artifacts. Upstream client SDKs are consumed as external package dependencies by the app members that use them.

## Boundary Rules
1. Repository-root configuration files own cross-member tooling/workspace behavior.
2. Repository-root `pyproject.toml` owns cross-member Python quality tooling policy for Ruff, ty, pytest, and import-linter.
3. Python workspace member `pyproject.toml` files retain package metadata, dependency declarations, build configuration, and member-required runtime declarations.
4. `packages/contracts` must not contain application business logic.
5. `infra` must not contain application business logic.
6. `apps/api/src/shared` contains reusable technical capabilities only.
7. Runtime configuration source is `.env` through `pydantic-settings`; YAML is not runtime config.
8. `apps/api/src/modules/knowledge_graph` remains sole owner of graph persistence models/repositories.
9. `apps/api/src/modules/search`, `apps/api/src/modules/ingestion`, and `apps/api/src/modules/taxonomy` access graph truth through service ports only.
10. `apps/api/src/modules/taxonomy` owns taxonomy persistence plus taxonomy view API contracts.
11. `apps/api/src/modules/taxonomy_classification` owns job-queue-backed classification orchestration and does not own graph/taxonomy persistence projections.
12. `apps/api/src/modules/**` must not import `apps/api/src/entrypoints/**`.
13. `apps/cli` owns local review/submission flow and must not own backend persistence/runtime concerns.
14. `human_workspace` assets are not authoritative online API/runtime contracts.
15. `apps/knowledge_corpus` is isolated local/offline ownership and not imported by online apps.
16. `apps/source_pipeline` owns project-level source-processing runtime and remains source-agnostic within this repository boundary.
17. `apps/source_pipeline` must not import `apps/api/src/entrypoints/**`.
18. `apps/source_pipeline` interacts with the online knowledge system only through accepted HTTP contracts and must not import `apps/api/src/modules/ingestion/**`, `apps/api/src/modules/knowledge_graph/**`, or write knowledge database tables directly.
19. `apps/web` owns public web HTTP endpoints and must not import `apps/api/src/**` or `apps/mcp/src/**`; it interacts with `apps/api` through the generated internal API client over Docker-network HTTP and with MCP usage summaries through internal HTTP only.
20. `apps/mcp` owns public MCP endpoints and must not import `apps/api/src/**`; it interacts with `apps/api` through generated internal API client artifacts over Docker-network HTTP.
21. `apps/mcp` must not persist, log, or expose raw Logto personal access tokens.
22. `apps/web` owns browser-facing Dashboard token lifecycle endpoints and must not directly read MCP usage database tables; it consumes MCP usage through an internal MCP service endpoint.
23. `apps/mcp` owns internal MCP usage-summary reads for dashboard consumption and accepts only PAT fingerprints for those reads, not raw personal access tokens.
24. `apps/mcp` may access only MCP-owned usage tables in the dedicated MCP PostgreSQL database and must not read or write graph, taxonomy, ingestion, source-pipeline, or job-queue linkage tables directly.
25. `apps/mcp` owns MCP usage persistence migrations through its own Alembic environment and must not register MCP persistence models in `apps/api` migration metadata.

## Governance Anchors
- Architecture constraints: `03-architecture-constraints`.
- Minimal quality gates: lint/format, typecheck, test, contract drift.
- Python quality tooling policy: repository-root `pyproject.toml`.
- Dependency-direction enforcement: API `import-linter` contracts in repository-root `pyproject.toml`.
