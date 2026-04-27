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
- Each persistence-owning app owns its own Alembic `env.py` as the metadata-entry boundary for migration autogeneration and upgrade execution.
- Alembic configuration and revision assets are app-local: online API schema under `apps/api/alembic.ini` and `apps/api/alembic/**`, knowledge corpus under `apps/knowledge_corpus/alembic.ini` and `apps/knowledge_corpus/alembic/**`, source pipeline under `apps/source_pipeline/alembic.ini` and `apps/source_pipeline/alembic/**`, and public MCP usage persistence under `apps/mcp/alembic.ini` and `apps/mcp/alembic/**`.
- Alembic environments must only scan database objects owned by their app. Apps that own only a dedicated database's default PostgreSQL schema must not enable repository-wide schema scanning.
- Migration execution in this repository is performed through governed script entrypoints under `scripts/alembic-*.sh`.
- Ad hoc migration execution paths outside governed entrypoints are out of baseline policy.

## Metadata Registration Contract
- Alembic target metadata uses the owning app's metadata object.
- All ORM modules participating in schema autogeneration must be import-registered in migration context.
- Metadata registration must include persistence models required by active schema projection designs.
- App-local migration metadata must not register persistence models owned by another app.

## Migration Connection Policy
- Migration execution uses migration-role credentials, separate from runtime app-role credentials.
- Migration connection configuration is app-local. Online API migrations use `KNOWLEDGE_API_MIGRATION_DATABASE_URL`; MCP usage migrations use `KNOWLEDGE_MCP_MIGRATION_DATABASE_URL`; knowledge corpus and source pipeline use their own migration URL settings.
- Migration settings consume the URL value directly and do not assemble URLs from component fields.
- Login role provisioning belongs to database bootstrap or explicit infrastructure convergence scripts. Alembic environments may create app-owned schemas only when the app intentionally owns non-default schemas, but they must not create login roles.

## Revision and Ordering Policy
- Revisions are linear by default in V1 baseline.
- Extension-enabling revisions that provide required types/operators must execute before dependent schema revisions.
- For `pgvector`, `CREATE EXTENSION IF NOT EXISTS vector` must be established before vector-typed schema operations.
- Extension downgrade removal is not part of V1 baseline policy unless an explicit future governance decision changes it.
- Table/column/index constraints that are representable in ORM metadata use governed autogenerate flow as the default.
- Database constructs that are not reliably derivable from ORM metadata, such as accepted cross-table trigger enforcement, use dedicated hand-authored migrations scoped only to those constructs.

## Failure and Blocking Policy
- Migration failure blocks release progression and blocks dependent runtime rollout.
- Known migration errors fail explicitly and remain observable in logs.
- Partial silent progression after migration failure is forbidden.

## Validation
- Migration metadata load resolves all participating schema models.
- Governed script entrypoints can run autogenerate and upgrade flows in development and production environments.
- Extension dependency ordering is satisfied for vector-dependent schema revisions.
- MCP usage migrations run from `apps/mcp` Alembic against the dedicated MCP database, maintain an MCP-owned version table, and do not depend on API Alembic metadata registration.
