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
- Scope/Boundaries: compose layering, network exposure, migration workflow, PostgreSQL image strategy, extension enablement, repository-managed accepted service provisioning, and failure policy.
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006.

## Deployment Topology (MVP)
- Production external exposure is restricted to the shared host-level reverse proxy on `80/443`.
- Development exposes `web` on `5174`, `api` on `8001`, and `db` on host `5432` for local debugging and SQL tooling.
- `db` remains internal-only in production.
- Knowledge corpus uses its own dedicated PostgreSQL service and does not share the online graph database service.
- Source pipeline uses its own dedicated PostgreSQL service and does not share the online graph database service.
- Development may expose the knowledge corpus PostgreSQL service on a separate host port for local tooling; it must not reuse the online database host port.
- Development may expose the source pipeline PostgreSQL service on a separate host port for local tooling; it must not reuse the online database or knowledge corpus host ports.
- `redis` remains internal-only in both environments and is provided by a project-managed service definition.
- Production runtime process topology is fixed to three backend process containers: one `api` container, one `worker` container, and one `orchestrator` container.
- Development starts `api` and `worker` by default; `orchestrator` is an explicit opt-in profile because local development must not accidentally submit source-pipeline jobs to the shared queue.
- Horizontal scaling is not an MVP requirement for `api`, `worker`, or `orchestrator`; production baseline keeps one running container per role.
- Production search read chain is `shared proxy -> nginx -> web -> api -> OpenAI Embeddings API + db`.
- Production ingestion write chain is `api -> redis -> worker -> OpenAI Embeddings API + db`.
- Development search read chain is `web -> api -> OpenAI Embeddings API + db`.
- Development ingestion write chain is `api -> redis -> worker -> OpenAI Embeddings API + db`.
- Migration is a dedicated one-shot job and not part of API startup.

## Network Boundaries
- `backend` network is internal-only and contains `db`, repository-managed data services, one-shot migration jobs, `redis`, `api`, `worker`, and production or explicitly enabled `orchestrator`.
- Knowledge corpus PostgreSQL may share a Docker network with other internal services or use its own internal network, but it must remain a separate service identity from the online graph database and must not reuse the `postgres` service name or lifecycle.
- Accepted first-version service names for the knowledge corpus database path are `knowledge_corpus_db` and `knowledge_corpus_migrate`.
- Source pipeline PostgreSQL may share a Docker network with other internal services or use its own internal network, but it must remain a separate service identity from the online graph database and must not reuse the `postgres` service name or lifecycle.
- Accepted first-version service names for the source pipeline database path are `source_pipeline_db` and `source_pipeline_migrate`.
- `edge` network contains `web`, `api`, `worker`, and the project-local `nginx` app gateway.
- Production connects the project-local `nginx` app gateway to the external shared `proxy` network with a stable `knowledge-nginx` alias. It must not publish host `80/443` ports directly.
- Production connects `orchestrator` to the external shared `proxy` network only for `job-queue-mcp` reverse-proxy hostnames. Development does not connect `orchestrator` to `proxy` by default.
- Development adds `db` to `edge` for host port publishing while keeping service-to-service database access on `backend`.
- Cross-service access must follow network boundaries rather than host port access.
- Development host access to PostgreSQL is for local tooling only; container-to-container database access still uses Docker service DNS (`postgres`) on `backend`.
- API and worker access Redis through Docker service DNS (`redis`) on `backend`, not host-local `localhost`.
- API and worker require outbound HTTPS egress for OpenAI Embeddings API access.

## Compose Layering Strategy
- `compose.base.yml`: shared service definitions plus logical network and volume keys. It must not own the compose project name, environment-specific image tags, explicit Docker volume names, or explicit Docker network names.
- `compose.dev.yml`: development-only overrides with project name `knowledge-dev`, development image tags, source mounts, debug commands, direct local port exposure, no `nginx` service, and opt-in `orchestrator` profile.
- `compose.prod.yml`: production-only overrides with project name `knowledge-prod`, production image tags, runtime restart policy, project-local `nginx` app gateway, shared `proxy` network attachment, and production external volume bindings.
- `compose.test.yml`: isolated test topology with project name `knowledge-test` and test image tags.
- `compose.prod.yml` must override accepted long-running and one-shot source-pipeline services with production image tags and production external volume binding for source-pipeline data.
- Migration autogeneration uses the same base+dev layering and does not use a dedicated compose overlay file.
- Repository-managed local/offline apps may add dedicated infrastructure services when those services are part of accepted repository app boundaries; knowledge corpus PostgreSQL is one such service.
- The accepted first-version compose baseline includes `knowledge_corpus_db` as a dedicated PostgreSQL service and `knowledge_corpus_migrate` as a dedicated one-shot migration job for `apps/knowledge_corpus`.
- The accepted first-version compose baseline includes `source_pipeline_db` as a dedicated PostgreSQL service, `source_pipeline_migrate` as a dedicated one-shot migration job, and `orchestrator` as the dedicated long-running runtime for `apps/source_pipeline`.

## Volume Lifecycle Policy
- Development and test use non-external project-scoped compose volumes and support optional volume cleanup through an explicit destroy flag.
- Production uses external volumes that are managed outside compose lifecycle and are not disposable through routine compose down.
- PostgreSQL and Redis persistent data in production must bind to external named volumes.
- Repository-managed production entrypoints must ensure accepted external production volumes exist before invoking compose operations against the production overlays.
- Redis mounts an explicit logical volume key in compose baselines to prevent anonymous-volume drift.

## Container Build Strategy
- `db` uses a custom PostgreSQL Dockerfile and is the extension package baseline owner.
- `api` uses a custom Dockerfile.
- `worker` reuses the same API image with role-specific command override.
- `orchestrator` uses its own custom Dockerfile built from `apps/source_pipeline`.
- Single-image policy is required for `api` and `worker`; runtime role is selected only by startup command.
- The API image installs the locked dependency set required for runtime and migration autogeneration tooling.
- The source-pipeline image installs the locked dependency set required for runtime and migration autogeneration tooling.
- `redis` uses fixed-tag official image `redis:7-bookworm`.
- `web` uses a custom Dockerfile with separate dev/prod targets.
- `nginx` uses a fixed-tag official image in production and does not use a custom Dockerfile.

## Process Role Command Contract
- `api` and `worker` must each have a stable, role-specific startup command suitable for direct mapping to Kubernetes `Deployment.spec.template.spec.containers[].command/args`.
- `orchestrator` must have a stable startup command suitable for direct mapping to Kubernetes `Deployment.spec.template.spec.containers[].command/args`.
- Compose files must reference role startup commands instead of embedding long inline runtime invocation details per environment.
- API role command owns API logging bootstrap and then starts FastAPI serving.
- Worker role command owns worker logging bootstrap and then starts Dramatiq worker serving.
- Orchestrator role command owns source-pipeline runtime bootstrap and then starts the long-running polling loop.

## Startup and Gating Order
- Required startup order is fixed:
  1. `db` and `redis` reach healthy state.
  2. `migrate` one-shot job runs and exits successfully.
  3. `api` and `worker` start.
  4. `web` starts.
  5. Production `nginx` starts after `api` and `web` are started.
- Knowledge corpus startup/migration order is separate from the online stack:
  1. `knowledge_corpus_db` reaches healthy state.
  2. `knowledge_corpus_migrate` one-shot job runs and exits successfully.
  3. External local scripts/programs may use the knowledge corpus library against the migrated database.
- Source pipeline startup/migration order is separate from the online stack:
  1. `source_pipeline_db` reaches healthy state.
  2. `source_pipeline_migrate` one-shot job runs and exits successfully.
  3. Production `orchestrator`, or development `orchestrator` when the profile is explicitly enabled, starts against the migrated source-pipeline database.
- `api` must not auto-run migrations.
- `apps/knowledge_corpus` does not own a long-running application container in first version, so its runtime contract ends at migrated database availability plus library usage from external local processes.
- `apps/source_pipeline` owns one long-running `orchestrator` container and one separate migration job.
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
- Configuration model remains `.env`-driven runtime settings through `pydantic-settings`.
- Environment files use `.env.example`, `.env.dev`, `.env.prod`, and `.env.test` naming.
- Only `.env.example` is tracked in version control; `.env.dev`, `.env.prod`, and `.env.test` remain local operator files.
- Sensitive values are provided through runtime environment variables or local `.env` files and are not committed.
- Compose commands inject environment values through outer `docker compose --env-file ...` invocation; service definitions must not declare `env_file`.
- Application code, test code, and migration code read only current process environment and must not load `.env` files directly.
- Queue and embedding runtime configuration include:
  - `KNOWLEDGE_API_REDIS_URL` with backend-network address `redis://redis:6379/0`
  - `KNOWLEDGE_API_EMBEDDING_API_URL` using OpenAI embeddings endpoint
  - `KNOWLEDGE_API_EMBEDDING_MODEL` set to `text-embedding-3-small`
  - `KNOWLEDGE_API_EMBEDDING_API_KEY` from runtime secret injection
- Production web runtime configuration sets `VITE_API_BASE_URL` to the same-origin `/api` path served by the project-local `nginx` app gateway.
- Database runtime configuration uses direct URL fields:
  - `KNOWLEDGE_API_DATABASE_URL` for API and worker runtime database access
  - `KNOWLEDGE_API_MIGRATION_DATABASE_URL` for migration-role execution paths
  - Separate app-specific URL fields for knowledge corpus runtime and migration execution; knowledge corpus must not reuse the online API/worker database URL names
  - Separate app-specific URL fields for source pipeline runtime and migration execution; source pipeline must not reuse the online API/worker database URL names
- Knowledge corpus database configuration uses:
  - `KNOWLEDGE_CORPUS_DATABASE_URL` for external local processes that import `apps/knowledge_corpus`
  - `KNOWLEDGE_CORPUS_MIGRATION_DATABASE_URL` for `knowledge_corpus_migrate`
- Source pipeline database configuration uses:
  - `SOURCE_PIPELINE_DATABASE_URL` for the long-running `orchestrator` runtime
  - `SOURCE_PIPELINE_MIGRATION_DATABASE_URL` for `source_pipeline_migrate`
- Tracked environment files must carry the knowledge corpus and source pipeline URL fields alongside the online stack URL fields when those repository-managed app services are enabled.

## Failure Policy
- Known startup failures must fail explicitly and stop rollout progression.
- Silent fallback and partial startup in known invalid states are forbidden.
- Error details must remain observable in logs for debugging.
- Ingestion enqueue failures are logged and observable while accepted-ingestion response semantics remain unchanged.

## Deferred to Later Phases
- Backup and restore strategy definition.
- Replication, failover, and multi-node PostgreSQL topology.
- Platform-specific deployment targets beyond Docker Compose baseline.
