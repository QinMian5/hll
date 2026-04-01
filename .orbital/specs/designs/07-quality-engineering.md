---
abstract: Quality engineering governance baseline for MVP phase-1 across backend and frontend.
out_of_scope: Detailed unit-test writing techniques, deployment topology internals, and advanced CI matrix design.
---

# Design: 07-quality-engineering

## Active Truth Policy
- This document stores only currently accepted quality engineering decisions.
- Superseded rules are removed from active text.

## Context
- Purpose: define a practical and enforceable MVP quality governance baseline.
- Scope: toolchain policy, gate policy, execution stages, and ownership boundaries.
- Related references:
  - [`03-architecture-constraints.md`](./03-architecture-constraints.md)
  - [`06-deployment-docker.md`](./06-deployment-docker.md)
  - [`unit-test-best-practice.md`](./unit-test-best-practice.md)

## Quality Objectives
- Keep feedback loops fast for MVP delivery.
- Preserve strong static quality signals for early defect detection.
- Enforce contract consistency between backend and frontend.
- Keep governance extensible for later hardening phases.

## Governance Scope and Ownership
- This document is the quality governance source of truth.
- Architecture constraints remain governed by `03`.
- Deployment structure remains governed by `06`.
- Unit-test writing practices remain governed by `unit-test-best-practice`.

## Phase-1 Required Gates
- `lint/format`
- `typecheck`
- `test`
- `contract drift`
- `commit message lint`

## Tooling Policy
### Git Hook Manager
- Git hooks are managed by pre-commit.
- Hook source of truth is `.pre-commit-config.yaml`.

### Backend Python
- Lint/format tool is Ruff.
- Ruff scope for gates is only `apps/api/src`.
- Ruff select set: `E,F,I,B,UP,SIM,C4,PIE,RUF,ANN`.
- Ruff ignore set: `B008`.
- `ruff format` is for local formatting; CI gate runs read-only lint checks.

### Backend Tests
- Test runner is pytest.
- Default blocked gate runs only backend unit tests (`apps/api/tests/unit`).
- Integration and contract tests are present but excluded from default blocked gate.

### Backend Type Checking
- Type checker is `ty`.
- Default blocked scope is only `apps/api/src`.

### Frontend
- Frontend lint/format tool is Biome.
- Local development may run auto-fix commands.
- CI must run read-only validation commands.
- `lint/check` are validation-only commands.
- `fix/format` are write commands.

## Execution Model by Stage
### Local Development
- Developers may run fix/format commands before validation gates.
- Recommended local sequence: `fix/format -> lint -> typecheck -> test -> contract drift`.
  - Gate mapping:
    - `lint/format` -> `scripts/lint.sh` for read-only checks and `make fix`/`make format` for local writes
    - `contract drift` -> `scripts/contracts-check.sh`

### Pre-commit
- Pre-commit executes local write/fix and type validation hooks before commit.
- Hook set is:
  - `uv run --project apps/api ruff format`
  - `uv run --project apps/api ruff check --fix`
  - `uv run --project apps/api ty check`
  - `pnpm --dir apps/web exec biome check --write`
  - `pnpm --dir apps/web exec tsc --noEmit`
  - `pnpm --dir apps/web exec commitlint --config commitlint.config.cjs --edit`
- Filename passing behavior:
  - Code-quality hooks set `pass_filenames: false`.
  - Code-quality hooks run without staged filename arguments.
  - Commit message hook runs at `commit-msg` stage and consumes the commit message filename.
- Commit message contract:
  - Commit messages must match `type(scope): description`.
  - Scope is required.

### CI
- CI is fail-fast and blocking for:
  - `lint`
  - `typecheck`
  - `test` (backend unit-only + frontend test command)
  - `contract drift`
  - `commit message lint`
- CI validation commands are read-only and do not rewrite files.

## Failure and Flake Policy
- Gate failures are blocking.
- Error outputs must preserve original tool errors.
- No silent failure swallowing is allowed.
- Flaky-test quarantine policy is deferred to later phases.

## Release Gate Position (Current)
- Release gate currently does not require `migrate` or Docker compose smoke checks.
- These checks are reserved for future hardening phases.

## Deferred to Later Phases
- Coverage threshold governance.
- Extended integration/E2E gate matrices.
- Full architecture lint automation.
- Release-time migration/smoke blocking gates.
- Advanced flaky quarantine lifecycle policy.
