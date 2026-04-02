---
abstract: Docker-based deployment design for MVP phase-1 across development and production environments.
out_of_scope: Kubernetes orchestration, backup/restore policy details, and high-availability multi-region architecture.
---

# Design: 06-deployment-docker

## Active Truth Policy
- This document defines only currently accepted deployment decisions for MVP phase-1.
- Superseded deployment choices are removed instead of described as transition history.
- This document defines deployment architecture boundaries, not implementation scripts.

## Context
- Purpose: define a reproducible Docker deployment model for dev and prod with explicit startup order and migration gating.
- Scope/Boundaries: compose layering, network exposure, migration workflow, PostgreSQL image strategy, extension enablement, and failure policy.
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006.

## Deployment Topology (MVP)
- Production external exposure is restricted to `80/443` through `Nginx`.
- Development exposes `web` on `5173` and `api` on `8000` directly for debugging.
- `db` remains internal-only in both environments.
- `redis` remains internal-only in both environments and is provided by a project-managed service definition.
- Production search read chain is `nginx -> web -> api -> db`.
- Production ingestion write chain is `api -> redis -> worker -> db`.
- Development search read chain is `web -> api -> db`.
- Development ingestion write chain is `api -> redis -> worker -> db`.
- Migration is a dedicated one-shot job and not part of API startup.

## Network Boundaries
- `backend` network is internal-only and contains `db`, `redis`, `migrate`, `api`, and `worker`.
- `edge` network contains `web`, `api`, and `nginx` (production only for `nginx`).
- Cross-service access must follow network boundaries rather than host port access.
- API and worker access Redis through Docker service DNS (`redis`) on `backend`, not host-local `localhost`.

## Compose Layering Strategy
- `compose.base.yml`: shared service definitions and common network/volume baseline, including `redis` and `worker`.
- `compose.dev.yml`: development-only overrides (source mounts, debug commands, direct local port exposure, no `nginx` service).
- `compose.prod.yml`: production-only overrides (runtime restart policy, `nginx` edge service, `80/443` exposure).
- Migration autogeneration uses the same base+dev layering and does not use a dedicated compose overlay file.

## Volume Lifecycle Policy
- Development uses non-external volumes and supports optional volume cleanup through an explicit destroy flag.
- Production uses external volumes that are managed outside compose lifecycle and are not disposable through routine compose down.
- PostgreSQL persistent data in production must bind to an external named volume.

## Container Build Strategy
- `db` uses a custom PostgreSQL Dockerfile and is the extension package baseline owner.
- `api` uses a custom Dockerfile.
- `worker` reuses the API image with Dramatiq worker command override.
- The API image installs the locked dependency set required for runtime and migration autogeneration tooling.
- `redis` uses fixed-tag official image `redis:7-bookworm`.
- `web` uses a custom Dockerfile with separate dev/prod targets.
- `nginx` uses a fixed-tag official image in production and does not use a custom Dockerfile.

## Startup and Gating Order
- Required startup order is fixed:
  1. `db` and `redis` reach healthy state.
  2. `migrate` one-shot job runs and exits successfully.
  3. `api` and `worker` start.
  4. `web` starts.
- `api` must not auto-run migrations.
- Startup dependency control must use `healthcheck + depends_on`.
- `sleep`-based wait logic is forbidden.

## PostgreSQL Image Strategy
- Production and development both use a custom PostgreSQL image.
- Extension package availability is owned by the PostgreSQL Dockerfile.
- New extension adoption is done by editing the PostgreSQL Dockerfile and rebuilding a versioned image.
- Runtime dynamic package installation in running database containers is not part of the baseline.

## Extension Lifecycle Policy
- Extension enablement is managed through Alembic migrations.
- Baseline extension migration policy:
  - `upgrade`: `CREATE EXTENSION IF NOT EXISTS vector`
  - `downgrade`: no-op for extension removal
- Extension migration must execute before schema migrations that depend on extension-provided types or operators.

## Database Privilege Model
- Role split is required:
  - `migration role`: DDL and extension enablement authority
  - `app role`: runtime read/write authority only
- Application runtime credentials must not hold extension-creation privileges.

## Release Workflow Policy
- Every release automatically runs migration as a one-shot deployment step.
- API rollout is allowed only after migration succeeds.
- Migration failure blocks release progression (fail-fast).

## Configuration and Secrets Boundary
- Configuration model remains `committed YAML + runtime env`.
- Environment files use `.env.example`, `.env.dev`, and `.env.prod` naming.
- Environment template files (`.env.example`, `.env.dev`, `.env.prod`) are tracked in version control.
- Sensitive values are provided through runtime environment variables or `.env` and are not committed.
- Compose injects environment values but does not become an additional business configuration source.
- Queue and embedding runtime configuration include:
  - `REDIS_URL` with backend-network address default `redis://redis:6379/0`
  - `EMBEDDING_API_URL` default `https://api.openai.com/v1/embeddings`
  - `EMBEDDING_MODEL` default `text-embedding-3-small`
  - `EMBEDDING_API_KEY` from runtime secret injection

## Failure Policy
- Known startup failures must fail explicitly and stop rollout progression.
- Silent fallback and partial startup in known invalid states are forbidden.
- Error details must remain observable in logs for debugging.
- Ingestion enqueue failures are logged and observable while accepted-ingestion response semantics remain unchanged.

## Deferred to Later Phases
- Backup and restore strategy definition.
- Replication, failover, and multi-node PostgreSQL topology.
- Platform-specific deployment targets beyond Docker Compose baseline.
