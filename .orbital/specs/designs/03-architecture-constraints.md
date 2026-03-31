---
abstract: MVP phase-1 architecture constraints for fast delivery with extensible boundaries.
out_of_scope: Detailed error code taxonomy, advanced CI matrices, and full-scale architecture lint automation.
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
- Backend layering is fixed to `api -> service -> repo`.
- Reverse dependency is forbidden in backend modules.
- Backend cross-module direct access to another module `repo/model` is forbidden.
- Backend cross-module interaction must go through the target module `service`.
- Frontend flow is fixed to `UI/page -> feature service -> generated contract client`.
- Frontend UI/component layer direct backend HTTP calls are forbidden.

## Naming Constraints
- Backend module file names are fixed: `api.py`, `service.py`, `repo.py`, `schema.py`, `model.py`.
- Transport/response models must not share names with ORM/domain models.
- Names must keep transport semantics and persistence semantics clearly separated.

## Configuration Constraints
- Allowed configuration sources are only: `YAML`, `.env`, and test-time code injection.
- No other runtime configuration source is allowed.
- Configuration precedence is fixed to `YAML < .env`.
- Configuration must be loaded through a single `pydantic-settings` entrypoint.
- Business code must not read environment variables directly.
- `.env` may override only fields declared in `pydantic-settings`.
- YAML stores non-sensitive configuration and is committed to git.
- `.env` stores sensitive values and is not committed to git.
- Test overrides must use the same `Settings` construction path.

## Error Handling Constraints
- Errors must fail explicitly.
- Silent error swallowing is forbidden.
- Known error states must not continue executing business logic.
- Errors must be logged for debugging.
- Error logs must preserve the original exception stack trace.
- Original stack trace is logged only; it is not returned in client response payloads.
- Detailed error code taxonomy and HTTP mapping are intentionally deferred.

## Minimal Quality Gates (Phase-1)
- `lint/format`
- `typecheck`
- `test`
- `contract drift`

## Deferred to Later Phases
- Detailed error code catalog and HTTP status mapping table.
- PR/main differentiated CI matrices.
- Broad test taxonomy expansion and complex marker governance.
- Full import-matrix automation and advanced architecture lint policies.
