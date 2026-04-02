---
abstract: MVP phase-1 architecture constraints for fast delivery with extensible boundaries.
out_of_scope: Module-level exhaustive error-code catalogs, advanced CI matrices, and full-scale architecture lint automation.
---

# Design: 03-architecture-constraints

## Active Truth Policy
- This document contains only currently accepted constraints.
- Superseded rules are removed instead of kept as transition history.
- Scope is limited to phase-1 MVP baseline constraints.

## Context
- Purpose: define the minimum enforceable architecture constraints for the current MVP phase.
- Scope/Boundaries: layering, dependency direction, naming, configuration, error handling, and minimal quality gates.
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006.

## Layering and Dependency Direction
- Backend runtime layering is fixed to `entrypoints -> modules -> shared`.
- `core` is foundational and can be imported by `entrypoints` and tooling entrypoints only.
- Reverse dependency is forbidden across these layers.
- Backend cross-module direct access to another module `repo/model` is forbidden.
- Backend cross-module interaction must go through the target module `service`.
- Frontend flow is fixed to `UI/page -> feature service -> generated contract client`.
- Frontend UI/component layer direct backend HTTP calls are forbidden.

## Naming Constraints
- Backend file names MUST express layer intent and module ownership.
- HTTP transport models MUST stay under the owning API-orchestration module (`search` or `ingestion`).
- Knowledge-graph domain DTOs MUST stay under `modules/knowledge_graph` and MUST NOT be named as HTTP transport schemas.
- Domain ports MAY use role-specific names (`ports.py`, `dto.py`) when they improve boundary clarity.
- Names must keep transport semantics and persistence semantics clearly separated.

## Configuration Constraints
- Allowed runtime configuration source is `.env` loaded through `pydantic-settings`.
- Runtime configuration must be loaded through one project entrypoint (`core/config.py`) and composed only from declared `Settings` fields.
- Business and orchestration modules must not read environment variables directly (`os.getenv`, `os.environ`, and equivalent direct environment reads are forbidden).
- YAML configuration sources are not part of runtime policy.
- Test overrides must use the same `Settings` construction path (`Settings(..., _env_file=...)`) and must not introduce alternate loaders.

## Dependency Injection Constraints
- Runtime dependency construction is centralized in `apps/api/src/entrypoints/runtime.py` and consumed by `entrypoints/api/providers.py` and `entrypoints/worker/actors.py`.
- `load_settings()` is a composition-root API and must be called only from composition entrypoints (`entrypoints/runtime.py`) and migration runtime entrypoint (`alembic/env.py`).
- Service and orchestration code must receive dependencies through explicit constructor/function parameters.
- Nullable dependency parameters used as runtime fallback (`dependency: T | None = None`) are forbidden in runtime paths.
- Implicit fallback expressions (`x or provider()`) are forbidden for dependency resolution in runtime paths.

## Error Handling Constraints
- Errors must fail explicitly.
- Silent error swallowing is forbidden.
- Known error states must not continue executing business logic.
- Errors must be logged for debugging.
- Error logs must preserve the original exception stack trace.
- Original stack trace is logged only; it is not returned in client response payloads.
- Deterministic error taxonomy and HTTP mapping governance are defined in `13-global-error-governance`.

## Minimal Quality Gates (Phase-1)
- `lint/format`
- `typecheck`
- `test`
- `contract drift`
- `dependency boundary checks (import-linter)`

## Deferred to Later Phases
- Per-module exhaustive error code catalogs beyond current global governance baseline.
- PR/main differentiated CI matrices.
- Broad test taxonomy expansion and complex marker governance.
- Full graph-wide architecture governance beyond the current `import-linter` boundary set.
