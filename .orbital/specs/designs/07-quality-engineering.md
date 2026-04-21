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
  - [`fastapi-unit-test-governance.md`](./fastapi-unit-test-governance.md)

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
- FastAPI HTTP endpoint test governance remains governed by `fastapi-unit-test-governance`.
- Repository-level aggregate commands are owned by `Makefile`.
- Root `pnpm` commands are limited to JS/TS-scoped actions.
- The default human-facing repository command surface is `make`, `make bootstrap`, `make fix`, `make test`, `make check`, `make integration`, environment lifecycle commands, and Alembic commands.

## Phase-1 Required Gates
- `lint/format`
- `typecheck`
- `test`
- `contract drift`
- `dependency boundary checks (import-linter)`
- `commit message lint`

## Tooling Policy
### Git Hook Manager
- Git hooks are managed by pre-commit.
- Hook source of truth is `.pre-commit-config.yaml`.
- Hook installation scope includes both `pre-commit` and `commit-msg`.

### Backend Python
- Lint/format tool is Ruff.
- Ruff scope for gates includes `apps/api`, `apps/knowledge_corpus`, and `apps/source_pipeline`.
- Ruff select set: `E,F,I,B,UP,SIM,C4,PIE,RUF,ANN,TID`.
- Ruff ignore set: `B008`.
- `ruff format` is for local formatting; CI gate runs read-only lint checks.

### Backend Tests
- Test runner is pytest.
- Default blocked gate runs backend unit tests for `apps/api/tests/unit`, `apps/knowledge_corpus/tests/unit`, and `apps/source_pipeline/tests/unit`.
- Integration and contract tests are present but excluded from default blocked gate.

### Backend Type Checking
- Type checker is `ty`.
- Default blocked scope includes `apps/api/src`, `apps/knowledge_corpus/src`, and `apps/source_pipeline/src`.

### Frontend
- JS/TS lint/format tool is Biome.
- Local development may run auto-fix commands.
- CI must run read-only validation commands.
- `lint/check` are validation-only commands.
- `fix/format` are write commands.
- Repository-level JS/TS scope includes `apps/web` and `packages/contracts`.
- Biome configuration source of truth is repository-root `biome.json`.
- Shared TypeScript base configuration is repository-root `tsconfig.base.json`.
- Repository-level TypeScript build entrypoint is repository-root `tsconfig.json`.

## Execution Model by Stage
### Local Development
- Developers may run fix/format commands before validation gates.
- Recommended local sequence: `make fix -> make test -> make check`.
- Recommended escalation for broader changes: `make integration`.
- Gate mapping:
  - `make fix` applies safe repository-wide fixes.
  - `make test` runs the default fast test suite.
  - `make check` runs the pre-submit aggregate checks, including lint, typecheck, default tests, and contract drift validation.
  - `make integration` runs the heavier integration test flow.
  - JS/TS-scoped commands:
    - `pnpm run js:lint`
    - `pnpm run js:fix`
    - `pnpm run js:format`
    - `pnpm run js:typecheck`
    - `pnpm run web:test`

### Pre-commit
- Pre-commit executes local write/fix and type validation hooks before commit.
- Hook set is:
  - `uv run --project apps/api ruff format`
  - `uv run --project apps/api ruff check --fix`
  - `uv run --project apps/api ty check apps/api/src`
  - `uv run --project apps/api lint-imports --config apps/api/pyproject.toml`
  - `uv run --project apps/knowledge_corpus ruff format apps/knowledge_corpus/src apps/knowledge_corpus/tests apps/knowledge_corpus/alembic`
  - `uv run --project apps/knowledge_corpus ruff check --fix apps/knowledge_corpus/src apps/knowledge_corpus/tests apps/knowledge_corpus/alembic`
  - `uv run --project apps/knowledge_corpus ty check --project apps/knowledge_corpus apps/knowledge_corpus/src`
  - `uv run --project apps/source_pipeline ruff format apps/source_pipeline/src apps/source_pipeline/tests apps/source_pipeline/alembic`
  - `uv run --project apps/source_pipeline ruff check --fix apps/source_pipeline/src apps/source_pipeline/tests apps/source_pipeline/alembic`
  - `uv run --project apps/source_pipeline ty check --project apps/source_pipeline apps/source_pipeline/src`
  - `pnpm run js:fix`
  - `pnpm run js:typecheck`
  - `pnpm exec commitlint --edit`
- Filename passing behavior:
  - Code-quality hooks set `pass_filenames: false`.
  - Code-quality hooks run without staged filename arguments.
  - Commit message hook runs at `commit-msg` stage and consumes the commit message filename.
- Commit message contract:
  - Commit messages must match `type(scope): description`.
  - Scope is required.
- Commitlint configuration source of truth is repository-root `commitlint.config.cjs`.

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
