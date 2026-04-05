---
abstract: Isolation strategy for PostgreSQL and Redis backed integration and migration tests.
out_of_scope: Production database hardening, backup strategy, and multi-node topology.
---

# Design: 11-test-database-isolation

## Active Truth Policy
- This document defines only active decisions for test database isolation.
- Superseded isolation approaches are removed from active text.

## Context
- **Purpose:** prevent integration and migration tests from mutating development or production runtime dependencies.
- **Scope/Boundaries:** test-only compose topology, test environment file policy, execution scripts, and runtime guardrails.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Topology and Environment Isolation
- Integration tests use a dedicated compose file: `infra/compose/docker-compose.test.yml`.
- Test compose topology includes PostgreSQL and Redis and does not include `api`/`web`.
- Test compose resources must use a dedicated compose project name and must not reuse dev/prod volumes or networks.
- Test runtime configuration is provided through current process environment, with repository scripts conventionally loading local-only `infra/env/.env.test` before invoking compose or pytest.

## Configuration Policy
- Test runtime settings use URL-first fields (`KNOWLEDGE_API_DATABASE_URL`, `KNOWLEDGE_API_MIGRATION_DATABASE_URL`) with no runtime fallback assembly.
- Test environment safety is governed by dedicated test-only environment values and isolated test compose topology.

## Migration Safety Policy
- Test migration entrypoint is `scripts/alembic-upgrade-test.sh`.
- Test migration configuration is loaded from `apps/api/alembic.ini`.
- Test migration runtime settings are loaded from current process environment through `pydantic-settings`.
- Alembic test runs execute only after test scripts inject the dedicated test environment into the process.

## Test Execution Policy
- Default fast test gate remains unit-only (`scripts/run-tests.sh`).
- PostgreSQL and Redis backed integration tests run through `scripts/test-integration.sh`.
- `scripts/test-integration.sh` sequence:
  1. Start isolated test PostgreSQL and Redis.
  2. Apply migrations to head.
  3. Execute `pytest tests/integration -m "integration and db and not slow"`.
  4. Tear down test stack (unless `KEEP_TEST_DB=1`).

## Fixture Contract
- Integration fixtures construct `Settings()` from current process environment only.
- Migration helpers construct `MigrationSettings()` from current process environment only.
- Session-scoped async engine is used for performance.
- Function-scoped transaction rollback provides per-test data isolation.
- Async sessions use `join_transaction_mode="create_savepoint"` and `expire_on_commit=False`.

## Validation
- Running `make test-integration` must not require `dev-up`.
- Migration and integration scripts fail fast when `.env.test` is missing.
- Integration tests that require DB are marked with `integration` + `db` markers.
- Test compose startup must bring both PostgreSQL and Redis to healthy state before integration execution.
- Integration suite includes Redis reachability smoke coverage under the isolated test stack.
