---
abstract: Isolation strategy for PostgreSQL-backed integration and migration tests.
out_of_scope: Production database hardening, backup strategy, and multi-node topology.
---

# Design: 11-test-database-isolation

## Active Truth Policy
- This document defines only active decisions for test database isolation.
- Superseded isolation approaches are removed from active text.

## Context
- **Purpose:** prevent integration and migration tests from mutating development or production databases.
- **Scope/Boundaries:** test-only compose topology, test environment file policy, execution scripts, and runtime guardrails.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Topology and Environment Isolation
- Integration tests use a dedicated compose file: `infra/compose/docker-compose.test.yml`.
- Test compose topology includes only PostgreSQL and does not include `api`/`web`.
- Test compose resources must use a dedicated compose project name and must not reuse dev/prod volumes or networks.
- Test runtime configuration is sourced from local-only `infra/env/.env.test`.

## Configuration Policy
- Test DB settings continue using component fields (`DB_HOST`, `DB_PORT`, `DB_NAME`, `APP_DB_*`, `MIGRATION_DB_*`).
- Test execution does not introduce committed full database URLs.
- Test guards require:
  - `DB_NAME` ends with `_test`
  - `APP_DB_USER` and `MIGRATION_DB_USER` end with `_test`
  - `DB_HOST` is from local allowlist (`localhost`, `127.0.0.1`)

## Migration Safety Policy
- Test migration entrypoint is `scripts/alembic-upgrade-test.sh`.
- Test migration configuration is loaded from `apps/api/alembic.ini`.
- Test migration uses `MIGRATION_DATABASE_URL` derived from component settings at runtime.
- Alembic in test mode (`APP_ENV=test`) enforces `_test` database and role suffix before migration execution.
- Alembic migration entrypoint requires `MIGRATION_DATABASE_URL` and does not fallback to runtime `DATABASE_URL`.

## Test Execution Policy
- Default fast test gate remains unit-only (`scripts/run-tests.sh`).
- PostgreSQL-backed integration tests run through `scripts/test-integration.sh`.
- `scripts/test-integration.sh` sequence:
  1. Start isolated test PostgreSQL.
  2. Apply migrations to head.
  3. Execute `pytest tests/integration -m "integration and db and not slow"`.
  4. Tear down test stack (unless `KEEP_TEST_DB=1`).

## Fixture Contract
- Integration fixtures resolve `.env.test`, set `SETTINGS_DOTENV_PATH`, and enforce test DB guardrails.
- Session-scoped async engine is used for performance.
- Function-scoped transaction rollback provides per-test data isolation.
- Async sessions use `join_transaction_mode="create_savepoint"` and `expire_on_commit=False`.

## Validation
- Running `make test-integration` must not require `dev-up`.
- Migration and integration scripts fail fast when `.env.test` is missing or guardrails are violated.
- Integration tests that require DB are marked with `integration` + `db` markers.
