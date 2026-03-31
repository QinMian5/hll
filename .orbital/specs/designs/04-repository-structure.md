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
- `apps/api`: FastAPI service source, runtime entrypoint, and API-side tests.
- `apps/web`: React web client source and web-side tests.
- `packages/contracts`: authoritative OpenAPI snapshot and generated client artifacts for frontend consumption.
- `infra`: deployment and environment template assets, not application business logic.
- `scripts`: repository automation scripts invoked by top-level governance commands.
- `.orbital/specs`: active requirements and design documents.

## Application Layout
### API Application (`apps/api`)
```text
apps/api/
  src/
    main.py
    core/
      config.py
      logging.py
      errors.py
      deps.py
    modules/
      knowledge/
      search/
    shared/
      db/
      integrations/
      utils/
  tests/
  pyproject.toml
  Dockerfile
```
- `apps/api/src/core/config.py` is the single `pydantic-settings` entrypoint.

### Web Application (`apps/web`)
```text
apps/web/
  src/
    app/
    features/
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
4. Runtime configuration sources are limited to git-tracked YAML and non-committed `.env`; test-only code injection is allowed only in tests.
5. `infra/env` contains deployment templates or examples and is not an additional runtime configuration source for application code.

## Governance Anchors
- Detailed architecture constraints are defined in `03-architecture-constraints`.
- Minimal phase-1 quality gates are `lint/format`, `typecheck`, `fast unit`, and `contract drift`.
- This document defines layout ownership only and does not redefine dependency policy details.

## Deferred to Later Phases
- Detailed CI stage matrices and environment-specific gate variants.
- Detailed error taxonomy and HTTP mapping.
- Full import-matrix automation and advanced architecture lint policies.
