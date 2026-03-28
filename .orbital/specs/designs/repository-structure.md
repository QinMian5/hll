---
abstract: Canonical repository structure and responsibility boundaries for the full-stack monorepo.
out_of_scope: Feature-level business behavior, endpoint semantics, and UI behavior specifications.
---

# Design: repository-structure

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the canonical monorepo structure, boundary rules, and governance flow for a single API service and a single web client with contract-driven integration.
- **Scope/Boundaries:** Covers repository paths, module boundaries, contract generation flow, governance commands, and quality gates. Does not define domain business rules or endpoint payload semantics.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:**
  - R-001 requires one consistent top-level governance contract.
  - R-002 requires one authoritative API contract source and deterministic generation.
  - R-003 requires contract-driven frontend API access.
  - R-004 requires explicit module boundaries and controlled shared capabilities.
  - R-005 requires reproducible local/CI quality gates and environment definitions.
  - R-006 requires active spec synchronization for behavior-changing structure decisions.
- **Detail Commitments:**
  - Repository uses strong governance naming: `apps/api`, `apps/web`, `packages/contracts`, `infra`, `scripts`.
  - Backend follows domain-oriented modules with standardized files per module.
  - Frontend uses feature-first top-level structure with technical layering inside each feature.
  - Frontend HTTP access is restricted to generated contract client consumption.
  - Contract artifacts (`openapi` snapshot and generated client/types) are versioned in repository.
  - `Makefile` and `scripts/` define the single governance command surface.
- **Update Rule:** Keep requirement statements stable when still valid. Apply detail changes only in this design module and linked plan documents.

## Inputs & Outputs
- **Inputs:**
  - Agreed governance baseline: strong governance monorepo.
  - Interface ownership decision: backend-exported OpenAPI as single source of truth.
  - Integration policy: frontend must consume generated contract client only.
  - Deployment policy: containerized standard deployment with environment layering.
- **Outputs:**
  - Canonical repository layout and directory responsibilities.
  - Contract generation and verification flow.
  - Governance command model and CI quality gate mapping.
- **Artifacts:**
  - `.orbital/specs/requirements.md`
  - `.orbital/specs/designs/repository-structure.md`
  - `.orbital/specs/plans/<date>-repository-structure-plan.md`

## Design Approach
- **Approach:** Balanced strong governance for a full-stack monorepo with one API service and one web app.
- **Key Elements:**
  1. Top-level structure:
     ```text
     repo/
       apps/
         api/
         web/
       packages/
         contracts/
       infra/
         compose/
         env/
       scripts/
       .github/workflows/
       .orbital/specs/
       Makefile
       README.md
     ```
  2. Backend structure (`apps/api`):
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
             api.py
             service.py
             repo.py
             schema.py
             model.py
           search/
             api.py
             service.py
             schema.py
         shared/
           db/
           integrations/
           utils/
       tests/
         unit/
         integration/
         contract/
       pyproject.toml
       Dockerfile
     ```
  3. Frontend structure (`apps/web`):
     ```text
     apps/web/
       src/
         app/
         features/
           knowledge/
             pages/
             components/
             hooks/
             services/
             types/
             utils/
           search/
             pages/
             components/
             hooks/
             services/
             types/
             utils/
         shared/
           ui/
           hooks/
           utils/
           config/
       tests/
         unit/
         integration/
       package.json
       Dockerfile
     ```
  4. Contract package structure (`packages/contracts`):
     ```text
     packages/contracts/
       openapi/
         openapi.json
       generated/
         types.ts
         client.ts
       scripts/
         export-openapi.sh
         generate-types.sh
         generate-client.sh
         verify-up-to-date.sh
       package.json
       README.md
     ```
  5. Governance and execution model:
     - `Makefile` exposes unified entrypoints (`bootstrap`, `dev`, `test`, `check`, `contracts`, `contracts-check`).
     - `scripts/` contains reusable automation scripts called by `Makefile`.
     - CI invokes repository-level commands and fails on contract drift or quality-gate failure.
- **Interactions:**
  - Backend exports OpenAPI snapshot into `packages/contracts/openapi/openapi.json`.
  - Contract generation scripts produce `generated/types.ts` and `generated/client.ts`.
  - Frontend feature services consume only generated client exports.
  - Infra compose/env assets configure runtime behavior without embedding business logic.
  - Repository-level quality gates validate contracts, tests, and build integrity before merge.

## Boundary Rules
1. `apps/web` SHALL NOT perform direct HTTP calls using ad hoc `fetch`/`axios` clients for backend APIs.
2. `packages/contracts` SHALL NOT contain business logic implementation.
3. `infra/` SHALL NOT contain application business logic.
4. `apps/api/src/shared` SHALL contain reusable technical capabilities only.
5. Backend module dependencies SHALL follow `api -> service -> repo` direction without reverse coupling.
6. Cross-domain backend interaction SHALL avoid direct repository coupling between unrelated modules.

## Error Handling and Validation
- Backend global error mapping is centralized in `apps/api/src/core/errors.py`.
- Backend logging and correlation rules are centralized in `apps/api/src/core/logging.py`.
- Frontend application shell hosts global error boundaries and request-error normalization.
- Contract validation gates ensure generated artifacts match authoritative OpenAPI snapshot.

## Validation
- **Checks:**
  1. Repository structure audit confirms all required top-level paths exist and no prohibited content is placed outside boundaries.
  2. Contract flow check confirms OpenAPI export and generated artifacts are synchronized.
  3. Frontend static checks enforce generated-client-only API access policy.
  4. CI executes repository-level quality gates from `Makefile` and reports deterministic outcomes.
  5. Spec semantic review confirms active docs contain only current accepted truth with no migration narration.
- **Evidence:**
  - Versioned spec documents under `.orbital/specs/`.
  - Successful local and CI execution logs for governance commands.
  - Zero-diff result from contract drift verification script.
  - Static analysis result proving no prohibited direct HTTP usage path.
