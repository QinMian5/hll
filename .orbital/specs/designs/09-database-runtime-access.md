---
abstract: Runtime database access boundary for asynchronous SQLAlchemy engine and session management.
out_of_scope: Domain schema definition, Alembic revision lifecycle strategy, and API response contract design.
---

# Design: 09-database-runtime-access

## Active Truth Policy
- This document defines only current runtime database-access decisions.
- Superseded runtime-access decisions are removed from active text.

## Context
- **Purpose:** Define the runtime boundary for asynchronous database access in API execution paths.
- **Scope/Boundaries:** Covers runtime database URL contract, async engine/session lifecycle baseline, and DI session entrypoint.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Runtime Access Boundary
- Runtime database access is implemented through `shared/db/session.py`.
- Runtime settings are loaded through the project `pydantic-settings` entrypoint from `.env`.
- Runtime assembly of engine/session dependencies is composed in `entrypoints/runtime.py`.
- Runtime access APIs expose asynchronous SQLAlchemy primitives and do not expose persistence internals beyond session scope.

## Connection URL Model
- Runtime connection configuration is maintained as `APP_DATABASE_URL`.
- Runtime settings consume the URL value directly and do not assemble URLs from component fields.
- Runtime settings do not define fallback composition paths for database URLs.

## Driver and Session Baseline
- Runtime driver is `postgresql+psycopg`.
- Runtime engine uses `create_async_engine`.
- Runtime session factory uses `async_sessionmaker(..., class_=AsyncSession)`.
- Runtime request/session dependency provides `AsyncSession` via an async generator boundary.

## Runtime Error Policy
- Missing required runtime database URL settings are startup errors.
- Connection setup failures fail explicitly and surface original exception context in logs.
- Runtime access layer must not silently fallback to alternate hidden connection sources.
- Runtime access layer must not resolve settings internally; settings are injected from the composition root.

## Ownership and Non-Responsibilities
- `shared/db/session.py` owns runtime access primitives (`engine`, `session factory`, `session generator`) and session lifecycle defaults.
- `entrypoints/runtime.py` owns runtime composition of these primitives with settings.
- This module does not own domain schema constraints or migration sequencing policy.

## Validation
- Runtime settings can load a valid `APP_DATABASE_URL` value using `postgresql+psycopg`.
- Engine and session factory can be instantiated without URL component assembly logic.
- Dependency entrypoint yields `AsyncSession` instances for service/repository usage.
