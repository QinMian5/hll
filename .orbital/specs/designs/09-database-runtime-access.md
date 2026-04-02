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
- **Scope/Boundaries:** Covers connection component model, runtime URL assembly rule, async engine/session lifecycle baseline, and DI session entrypoint.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Runtime Access Boundary
- Runtime database access is implemented through `shared/db/session.py`.
- Runtime settings are loaded through the project `pydantic-settings` entrypoint from `.env`.
- Runtime assembly of engine/session dependencies is composed in `entrypoints/runtime.py`.
- Runtime access APIs expose asynchronous SQLAlchemy primitives and do not expose persistence internals beyond session scope.

## Connection Component Model
- Runtime connection configuration is maintained as components:
  - `host`
  - `port`
  - `database`
  - `user`
  - `password`
- Runtime connection strings are assembled from these components at runtime.
- Runtime settings must not maintain an additional independently authored full URL value that can drift from components.

## Driver and Session Baseline
- Runtime driver is `postgresql+psycopg`.
- Runtime engine uses `create_async_engine`.
- Runtime session factory uses `async_sessionmaker(..., class_=AsyncSession)`.
- Runtime request/session dependency provides `AsyncSession` via an async generator boundary.

## Runtime Error Policy
- Missing required runtime connection components are startup errors.
- Connection setup failures fail explicitly and surface original exception context in logs.
- Runtime access layer must not silently fallback to alternate hidden connection sources.
- Runtime access layer must not resolve settings internally; settings are injected from the composition root.

## Ownership and Non-Responsibilities
- `shared/db/session.py` owns runtime access primitives (`engine`, `session factory`, `session generator`) and session lifecycle defaults.
- `entrypoints/runtime.py` owns runtime composition of these primitives with settings.
- This module does not own domain schema constraints or migration sequencing policy.

## Validation
- Runtime settings can construct a valid component-derived connection string using `postgresql+psycopg`.
- Engine and session factory can be instantiated without relying on duplicated hard-coded URL literals.
- Dependency entrypoint yields `AsyncSession` instances for service/repository usage.
