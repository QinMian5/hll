---
abstract: Governance for Alembic migration lifecycle, metadata loading, and role-scoped migration execution.
out_of_scope: Runtime request-session management, API business orchestration, and frontend integration behavior.
---

# Design: 10-migration-lifecycle-governance

## Active Truth Policy
- This document defines only current migration-governance decisions.
- Superseded migration decisions are removed from active text.

## Context
- **Purpose:** Define deterministic migration lifecycle behavior for schema evolution.
- **Scope/Boundaries:** Covers metadata registration, migration connection sourcing, revision sequencing, extension dependency ordering, and execution entrypoints.
- **Related Requirements:** R-001, R-002, R-005, R-006.

## Migration Governance Boundary
- Alembic `env.py` is the metadata-entry boundary for migration autogeneration and upgrade execution.
- Alembic configuration and revision assets are owned by `apps/api` at `apps/api/alembic.ini` and `apps/api/alembic/**`.
- Migration execution in this repository is performed through governed script entrypoints under `scripts/alembic-*.sh`.
- Ad hoc migration execution paths outside governed entrypoints are out of baseline policy.

## Metadata Registration Contract
- Alembic target metadata uses shared `Base.metadata`.
- All ORM modules participating in schema autogeneration must be import-registered in migration context.
- Metadata registration must include persistence models required by active schema projection designs.

## Migration Connection Policy
- Migration execution uses migration-role credentials, separate from runtime app-role credentials.
- Migration connection configuration is maintained as `MIGRATION_DATABASE_URL`.
- Migration settings consume the URL value directly and do not assemble URLs from component fields.

## Revision and Ordering Policy
- Revisions are linear by default in V1 baseline.
- Extension-enabling revisions that provide required types/operators must execute before dependent schema revisions.
- For `pgvector`, `CREATE EXTENSION IF NOT EXISTS vector` must be established before vector-typed schema operations.
- Extension downgrade removal is not part of V1 baseline policy unless an explicit future governance decision changes it.

## Failure and Blocking Policy
- Migration failure blocks release progression and blocks dependent runtime rollout.
- Known migration errors fail explicitly and remain observable in logs.
- Partial silent progression after migration failure is forbidden.

## Validation
- Migration metadata load resolves all participating schema models.
- Governed script entrypoints can run autogenerate and upgrade flows in development and production environments.
- Extension dependency ordering is satisfied for vector-dependent schema revisions.
