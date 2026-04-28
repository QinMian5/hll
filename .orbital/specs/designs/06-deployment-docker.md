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
- Related Requirements: R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Deployment Topology (MVP)
- Production external exposure is restricted to the shared host-level reverse proxy on `80/443`, routed through the project-local `nginx` app gateway to explicitly public web, public MCP, Logto, and webhook surfaces.
- Development exposes `web` on `5174`, `api` on `8001`, and `db` on host `5432` for local debugging and SQL tooling.
- `api`, `db`, and `redis` remain internal-only in production.
- Knowledge corpus uses its own dedicated PostgreSQL service and does not share the online graph database service.
- Source pipeline uses its own dedicated PostgreSQL service and does not share the online graph database service.
- MCP uses its own dedicated PostgreSQL service for durable usage records and does not share the online graph database service.
- Development may expose the knowledge corpus PostgreSQL service on a separate host port for local tooling; it must not reuse the online database host port.
- Development may expose source-pipeline and MCP PostgreSQL services on separate host ports for local tooling; they must not reuse the online database or knowledge corpus host ports.
- `redis` remains internal-only in both environments and is provided by a project-managed service definition.
- Production runtime process topology includes one private `api` container, one `worker` container, one public `web` BFF container, one public `mcp` container, one source-pipeline `orchestrator` container, one source-pipeline webhook receiver container, one taxonomy-classification runtime container, and one taxonomy-classification webhook receiver container. The production identity topology additionally includes self-hosted `logto-postgres`, `logto-seed`, and `logto` services for the `knowledge` OAuth authority.
- Development starts `api` and `worker` by default. Development also includes source-pipeline data and migration services as default app-local infrastructure. Source-pipeline and taxonomy-classification queue-connected runtimes are explicit opt-in profiles because local development must not accidentally submit jobs to the shared queue or expose webhook intake unintentionally.
- Horizontal scaling is not an MVP requirement for `api`, `worker`, source-pipeline runtimes, or taxonomy-classification runtimes; production baseline keeps one running container per role.
- Production search read chain is `shared proxy -> nginx -> web BFF -> api -> egress -> OpenAI Embeddings API + db`.
- Production MCP search chain is `shared proxy -> nginx -> mcp -> api -> egress -> OpenAI Embeddings API + db`, with `mcp -> logto` for PAT token exchange and access-token validation metadata.
- Production Dashboard token-management chain is `shared proxy -> nginx -> web BFF -> logto` for personal access token lifecycle operations and `web BFF -> mcp` over the backend network for usage summaries.
- Production ingestion write chain is `api -> redis -> worker -> egress -> OpenAI Embeddings API + db`.
- Development search read chain is `web BFF -> api -> OpenAI Embeddings API + db`.
- Development MCP search chain is `mcp -> api -> OpenAI Embeddings API + db`, with `mcp -> logto` for PAT token exchange and access-token validation metadata.
- Development Dashboard token-management chain is `web BFF -> logto` for personal access token lifecycle operations and `web BFF -> mcp` over the backend network for usage summaries.
- Development ingestion write chain is `api -> redis -> worker -> OpenAI Embeddings API + db`.
- Migration is a dedicated one-shot job and not part of API startup.

## Network Boundaries
- `backend` network is internal-only and contains the online database, repository-managed data services, one-shot migration jobs, `redis`, self-hosted Logto services, `api`, `web`, `mcp`, `worker`, production or explicitly enabled source-pipeline runtimes, and production or explicitly enabled taxonomy-classification runtimes.
- Knowledge corpus PostgreSQL may share a Docker network with other internal services or use its own internal network, but it must remain a separate service identity from the online graph database and must not reuse the `postgres` service name or lifecycle.
- Accepted first-version service names for the knowledge corpus database path are `knowledge_corpus_db` and `knowledge_corpus_migrate`.
- Source pipeline PostgreSQL may share a Docker network with other internal services or use its own internal network, but it must remain a separate service identity from the online graph database and must not reuse the `postgres` service name or lifecycle.
- Accepted first-version service names for the source pipeline database path are `source_pipeline_db` and `source_pipeline_migrate`.
- MCP PostgreSQL may share a Docker network with other internal services or use its own internal network, but it must remain a separate service identity from the online graph database and must not reuse the `postgres` service name or lifecycle.
- Accepted first-version service names for the MCP usage database path are `mcp_db` and `mcp_migrate`.
- `edge` network contains `web`, `mcp`, self-hosted Logto, enabled webhook receiver roles, and the project-local `nginx` app gateway.
- `egress` network contains only runtime roles that need outbound access to external HTTPS services. It is not used for public inbound exposure.
- Production connects the project-local `nginx` app gateway to the external shared `proxy` network with stable `knowledge-nginx`, `knowledge.orbitalis.org`, `knowledge-logto.orbitalis.org`, and `admin.knowledge-logto.internal.home.arpa` aliases. It must not publish host `80/443` ports directly.
- Production connects source-pipeline and taxonomy-classification result-consuming runtimes to `egress` for outbound `job-queue-mcp` API and token calls. These runtimes do not attach to the external shared `proxy` network.
- Production `nginx` routes the public application host to `web` and does not route public `/api/` paths to the private `api` container.
- Production `nginx` routes the public MCP endpoint path to `mcp` and does not route MCP traffic through the browser BFF.
- Production exposes webhook receiver roles through the project-local `nginx` app gateway on dedicated webhook paths. Receiver containers remain container-only and must not publish host ports directly.
- Production `nginx` uses Docker embedded DNS with variable-based upstreams for internal service targets so app-gateway routing re-resolves service names when upstream containers are recreated.
- Development adds `db` to `edge` for host port publishing while keeping service-to-service database access on `backend`.
- Cross-service access must follow network boundaries rather than host port access.
- Development host access to PostgreSQL is for local tooling only; container-to-container database access still uses Docker service DNS (`postgres`) on `backend`.
- Web BFF access to the private API uses Docker service DNS (`api`) on `backend`, not public hostnames.
- MCP service access to the private API uses Docker service DNS (`api`) on `backend`, not public hostnames.
- API and worker access Redis through Docker service DNS (`redis`) on `backend`, not host-local `localhost`.
- Web BFF access to Redis uses Docker service DNS (`redis`) on `backend`, not host-local `localhost`.
- MCP service access to Redis uses Docker service DNS (`redis`) on `backend`, not host-local `localhost`.
- Web BFF access to MCP usage-summary uses Docker service DNS (`mcp`) on `backend`, not public MCP hostnames.
- MCP attaches to both `edge` and `backend`: public MCP traffic enters only through `nginx` on `edge`, while MCP access to `api`, `redis`, `mcp_db`, and `logto` uses service DNS on `backend`.
- API and worker require outbound HTTPS egress for OpenAI Embeddings API access.
- Source-pipeline and taxonomy-classification result-consuming runtimes require outbound HTTPS egress for `job-queue-mcp` API and token access.

## Compose Layering Strategy
- `docker-compose.base.yml`: shared service definitions plus logical network and volume keys. It must not own the compose project name, environment-specific image tags, explicit Docker volume names, or explicit Docker network names.
- `docker-compose.dev.yml`: development-only overrides with project name `knowledge-dev`, development image tags, source mounts, debug commands, direct local port exposure, no `nginx` service, default source-pipeline `source_pipeline_db` and `source_pipeline_migrate` services, default `mcp` service, and explicit opt-in profiles for `orchestrator`, `source_pipeline_webhook_receiver`, `taxonomy_classification_runtime`, and `taxonomy_classification_webhook_receiver`.
- `docker-compose.prod.yml`: production-only overrides with project name `knowledge-prod`, production image tags, runtime restart policy, project-local `nginx` app gateway, public web BFF routing, public MCP routing, `nginx` shared `proxy` network attachment, and production external volume bindings.
- `docker-compose.test.yml`: isolated test topology with project name `knowledge-test` and test image tags.
- `docker-compose.prod.yml` must override accepted long-running and one-shot source-pipeline services with production image tags and production external volume binding for source-pipeline data.
- Migration autogeneration uses the same base+dev layering and does not use a dedicated compose overlay file.
- Repository-managed local/offline apps may add dedicated infrastructure services when those services are part of accepted repository app boundaries; knowledge corpus PostgreSQL is one such service.
- The accepted first-version compose baseline includes `knowledge_corpus_db` as a dedicated PostgreSQL service and `knowledge_corpus_migrate` as a dedicated one-shot migration job for `apps/knowledge_corpus`.
- The accepted first-version compose baseline includes `source_pipeline_db` as a dedicated PostgreSQL service, `source_pipeline_migrate` as a dedicated one-shot migration job, `orchestrator` as the dedicated long-running runtime for `apps/source_pipeline`, and `source_pipeline_webhook_receiver` as the dedicated webhook intake runtime for `apps/source_pipeline`. In development, `source_pipeline_db` and `source_pipeline_migrate` are default services, while `orchestrator` and `source_pipeline_webhook_receiver` are profile-gated runtimes.
- The accepted taxonomy-classification compose baseline uses the API database and API image with dedicated role commands for `taxonomy_classification_runtime` and `taxonomy_classification_webhook_receiver`.
- The accepted MCP compose baseline includes `mcp_db` as a dedicated PostgreSQL service, `mcp_migrate` as a dedicated one-shot migration job, and `mcp` as a dedicated long-running Python service that depends on `api`, `redis`, `mcp_db`, `logto`, and successful `mcp_migrate` completion.

## Volume Lifecycle Policy
- Development and test use non-external project-scoped compose volumes and support optional volume cleanup through an explicit destroy flag.
- Production uses external volumes that are managed outside compose lifecycle and are not disposable through routine compose down.
- PostgreSQL and Redis persistent data in production must bind to external named volumes.
- Repository-managed production entrypoints must ensure accepted external production volumes exist before invoking compose operations against the production overlays.
- Redis mounts an explicit logical volume key in compose baselines to prevent anonymous-volume drift.

## Container Build Strategy
- `db` uses a custom PostgreSQL Dockerfile and is the extension package baseline owner.
- `logto-postgres` uses the fixed official PostgreSQL image because Logto owns its own schema and does not use the repository app/migration role initialization script.
- `api` uses a custom Dockerfile.
- `worker` reuses the same API image with role-specific command override.
- `mcp` and `mcp_migrate` use the same custom Dockerfile built from `apps/mcp`.
- `mcp_db` uses the shared custom PostgreSQL Dockerfile with MCP-specific image tags in environment overlays.
- `taxonomy_classification_runtime` and `taxonomy_classification_webhook_receiver` reuse the same API image with role-specific command overrides.
- `orchestrator` and `source_pipeline_webhook_receiver` use the same custom Dockerfile built from `apps/source_pipeline`.
- Single-image policy is required for `api` and `worker`; runtime role is selected only by startup command.
- Single-image policy applies to taxonomy-classification API-side roles; runtime role is selected only by startup command.
- The API image installs the locked dependency set required for runtime and migration autogeneration tooling.
- The source-pipeline image installs the locked dependency set required for runtime and migration autogeneration tooling.
- API and source-pipeline image builds provide the local `job-queue-mcp` Python SDK package as a named build context so locked local-path SDK dependencies resolve inside Docker builds without vendoring SDK source into this repository.
- `redis` uses fixed-tag official image `redis:7-bookworm`.
- `web` uses a custom Dockerfile with separate dev/prod targets; the production target builds Vite assets and runs the Express BFF server.
- `nginx` uses a fixed-tag official image in production and does not use a custom Dockerfile.

## Process Role Command Contract
- `api` and `worker` must each have a stable, role-specific startup command suitable for direct mapping to Kubernetes `Deployment.spec.template.spec.containers[].command/args`.
- `orchestrator` and `source_pipeline_webhook_receiver` must each have a stable startup command suitable for direct mapping to Kubernetes `Deployment.spec.template.spec.containers[].command/args`.
- `taxonomy_classification_runtime` and `taxonomy_classification_webhook_receiver` must each have a stable startup command suitable for direct mapping to Kubernetes `Deployment.spec.template.spec.containers[].command/args`.
- Compose files must reference role startup commands. Long inline runtime invocation details stay out of environment-specific compose service definitions.
- API role command owns API logging bootstrap and then starts FastAPI serving.
- Worker role command owns worker logging bootstrap and then starts Dramatiq worker serving.
- Web role command starts the Express BFF server and serves the built Vite assets from the same process.
- MCP role command owns MCP logging bootstrap and then starts the Streamable HTTP MCP server.
- Orchestrator role command owns source-pipeline runtime bootstrap and then starts the long-running local event and reconcile loop.
- Source-pipeline webhook receiver role command owns source-pipeline webhook HTTP bootstrap and then starts the authenticated notification receiver.
- Taxonomy-classification runtime role command owns taxonomy-classification runtime bootstrap and then starts the long-running local event and reconcile loop.
- Taxonomy-classification webhook receiver role command owns taxonomy-classification webhook HTTP bootstrap and then starts the authenticated notification receiver.

## Startup and Gating Order
- Required startup order is fixed:
  1. Online and app-owned PostgreSQL services plus `redis` reach healthy state.
  2. Online PostgreSQL role bootstrap converges repository-managed login roles after `db` is healthy and before online migrations run.
  3. `migrate` and `mcp_migrate` one-shot jobs run after their owning PostgreSQL services are healthy and exit successfully before their dependent runtimes start.
  4. `api` and `worker` start after `migrate`.
  5. `web` and `mcp` start after their private dependencies are healthy; `mcp` additionally waits for `mcp_migrate`.
  6. Production `nginx` starts after `web`, `mcp`, enabled webhook receiver roles, and Logto are available.
- Knowledge corpus startup/migration order is separate from the online stack:
  1. `knowledge_corpus_db` reaches healthy state.
  2. `knowledge_corpus_migrate` one-shot job runs and exits successfully.
  3. External local scripts/programs may use the knowledge corpus library against the migrated database.
- Source pipeline startup/migration order is separate from the online stack:
  1. `source_pipeline_db` reaches healthy state.
  2. `source_pipeline_migrate` one-shot job runs and exits successfully.
  3. Production `orchestrator` and `source_pipeline_webhook_receiver`, or development `orchestrator` and `source_pipeline_webhook_receiver` when their profiles are explicitly enabled, start against the migrated source-pipeline database.
- Taxonomy-classification queue runtime startup uses the online API database migration gate:
  1. `db` reaches healthy state.
  2. `migrate` one-shot job runs and exits successfully.
  3. Production `taxonomy_classification_runtime` and `taxonomy_classification_webhook_receiver`, or development taxonomy-classification services when their profiles are explicitly enabled, start against the migrated API database.
- MCP startup/migration order is separate from the online graph database migration gate:
  1. `mcp_db` reaches healthy state.
  2. `mcp_migrate` one-shot job runs and exits successfully.
  3. `mcp` starts after `mcp_migrate` and its private runtime dependencies are available.
- `api` must not auto-run migrations.
- `apps/knowledge_corpus` does not own a long-running application container in first version, so its runtime contract ends at migrated database availability plus library usage from external local processes.
- `apps/source_pipeline` owns one long-running `orchestrator` container, one long-running source-pipeline webhook receiver container, and one separate migration job.
- `apps/api` owns one long-running taxonomy-classification runtime container and one long-running taxonomy-classification webhook receiver container.
- `apps/mcp` owns one long-running public MCP server container and one separate migration job.
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
- The MCP runtime uses a dedicated PostgreSQL service, database role, and URL. That role receives only the privileges required for the MCP usage ledger and must not reuse the API/worker runtime role.
- Online PostgreSQL role bootstrap creates or converges only online database roles.
- MCP database role bootstrap is owned by the dedicated `mcp_db` PostgreSQL service initialization.
- MCP migrations use `KNOWLEDGE_MCP_MIGRATION_DATABASE_URL`, own the default schema in the dedicated MCP database, and store their Alembic version row in that database.
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
- Production web runtime configuration provides BFF settings for the internal API base URL, Redis URL, Logto web application credentials, callback base URL, session cookie secret, secure-cookie policy, anonymous identity cookie policy, web quota limits, Logto Account API access, Logto Management API personal-access-token access, MCP usage-summary base URL, MCP usage-summary service-token acquisition, and PAT fingerprint secret.
- Web Dashboard token-management configuration uses:
  - `KNOWLEDGE_WEB_LOGTO_MANAGEMENT_API_BASE_URL` for Logto Management API user personal-access-token endpoints
  - `KNOWLEDGE_WEB_LOGTO_MANAGEMENT_TOKEN_URL` for the Logto client-credentials token endpoint used by the BFF Management API client
  - `KNOWLEDGE_WEB_LOGTO_MANAGEMENT_RESOURCE` and `KNOWLEDGE_WEB_LOGTO_MANAGEMENT_SCOPES` for Management API access-token audience and scope requests
  - `KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_ID` and `KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_SECRET` for the BFF Management API client
  - `KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_BASE_URL` for internal calls to the MCP service
  - `KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_TOKEN_URL` for the Logto client-credentials token endpoint used by the BFF usage-summary client
  - `KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_RESOURCE` and `KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_SCOPES` for usage-summary access-token audience and scope requests
  - `KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_ID` and `KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_SECRET` for the BFF usage-summary service client
  - `KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET` for computing MCP-compatible PAT fingerprints from Logto-returned token values
- Production MCP runtime configuration provides settings for the public MCP base URL, internal API base URL, Redis URL, dedicated MCP PostgreSQL database URL, Logto issuer, Logto token endpoint, Logto discovery URL, MCP API resource/audience, required search scope, Logto token-exchange client credentials, PAT fingerprint secret, MCP usage-summary resource/audience, required usage-summary scope, allowed usage-summary service client id, MCP quota limits, MCP allowed origins, and MCP usage-recording behavior.
- MCP internal usage-summary configuration uses:
  - `KNOWLEDGE_MCP_USAGE_SUMMARY_AUTH_RESOURCE` for the internal usage-summary API resource/audience
  - `KNOWLEDGE_MCP_USAGE_SUMMARY_REQUIRED_SCOPE` with value `usage:read`
  - `KNOWLEDGE_MCP_USAGE_SUMMARY_ALLOWED_CLIENT_ID` for the BFF service client allowed to call usage-summary reads
- Browser runtime configuration does not include the private API base URL.
- Database runtime configuration uses direct URL fields:
  - `KNOWLEDGE_API_DATABASE_URL` for API and worker runtime database access
  - `KNOWLEDGE_API_MIGRATION_DATABASE_URL` for migration-role execution paths
  - `KNOWLEDGE_MCP_DATABASE_URL` for MCP runtime access to MCP-owned usage tables only
  - `KNOWLEDGE_MCP_MIGRATION_DATABASE_URL` for MCP migration-role execution paths
  - Separate app-specific URL fields for knowledge corpus runtime and migration execution; knowledge corpus must not reuse the online API/worker database URL names
  - Separate app-specific URL fields for source pipeline runtime and migration execution; source pipeline must not reuse the online API/worker database URL names
- Knowledge corpus database configuration uses:
  - `KNOWLEDGE_CORPUS_DATABASE_URL` for external local processes that import `apps/knowledge_corpus`
  - `KNOWLEDGE_CORPUS_MIGRATION_DATABASE_URL` for `knowledge_corpus_migrate`
- Source pipeline database configuration uses:
  - `SOURCE_PIPELINE_DATABASE_URL` for the long-running `orchestrator` runtime
  - `SOURCE_PIPELINE_MIGRATION_DATABASE_URL` for `source_pipeline_migrate`
- Source pipeline Job Queue client configuration uses:
  - `SOURCE_PIPELINE_JOB_QUEUE_BASE_URL` for producer and result-read calls to `job-queue-mcp`
  - `SOURCE_PIPELINE_JOB_QUEUE_TOKEN_URL` for the Job Queue Logto client-credentials flow used by source-pipeline producer and result-reader calls
  - `SOURCE_PIPELINE_JOB_QUEUE_CLIENT_ID` and `SOURCE_PIPELINE_JOB_QUEUE_CLIENT_SECRET` for source-pipeline access to `job-queue-mcp`
  - `SOURCE_PIPELINE_JOB_QUEUE_RESOURCE` and `SOURCE_PIPELINE_JOB_QUEUE_SCOPES` for the Job Queue access-token audience and scope request
- Source pipeline webhook receiver configuration uses:
  - `SOURCE_PIPELINE_WEBHOOK_AUTH_ISSUER` for the `knowledge` Logto issuer trusted by the receiver
  - `SOURCE_PIPELINE_WEBHOOK_AUTH_RESOURCE` for the receiver API resource/audience
  - `SOURCE_PIPELINE_WEBHOOK_AUTH_DISCOVERY_URL` for container-to-container discovery when it differs from the public issuer URL
  - `SOURCE_PIPELINE_WEBHOOK_ALLOWED_CLIENT_ID` for the dedicated `job-queue-mcp` delivery client identity allowed to call the receiver
  - `SOURCE_PIPELINE_WEBHOOK_PUBLIC_PATH` for the project-local nginx path that routes to the receiver
- The source-pipeline webhook receiver does not receive the source-pipeline Job Queue producer/result-reader client secret because receiving webhook notifications does not require creating jobs or reading accepted results.
- Taxonomy classification Job Queue client configuration uses:
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_BASE_URL` for producer and result-read calls to `job-queue-mcp`
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_TOKEN_URL` for the Job Queue Logto client-credentials flow used by taxonomy-classification producer and result-reader calls
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_ID` and `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET` for taxonomy-classification access to `job-queue-mcp`
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_RESOURCE` and `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_SCOPES` for the Job Queue access-token audience and scope request
- These Job Queue producer/result-reader fields are present only on the taxonomy-classification runtime role and operator submission environment.
- Taxonomy classification webhook receiver configuration uses:
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME` for rejecting misrouted authenticated queue notifications before local event persistence
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_ISSUER` for the `knowledge` Logto issuer trusted by the receiver
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_RESOURCE` for the receiver API resource/audience
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_DISCOVERY_URL` for container-to-container discovery when it differs from the public issuer URL
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID` for the dedicated `job-queue-mcp` delivery client identity allowed to call the receiver
  - `KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_PUBLIC_PATH` for the project-local nginx path that routes to the receiver
- The taxonomy-classification webhook receiver does not receive the taxonomy-classification Job Queue producer/result-reader client secret because receiving webhook notifications does not require creating jobs or reading accepted results.
- Knowledge Logto provisioning includes dedicated machine-to-machine applications for `job-queue-mcp` webhook delivery to source-pipeline and taxonomy-classification receivers. Their client credentials are consumed by `job-queue-mcp` webhook subscription configuration, while receiver roles store only validation settings and allowed delivery client identities.
- Knowledge Logto provisioning includes one first-party application credential for MCP PAT token exchange. User-created personal access tokens remain user-owned credentials and are not modeled as machine-to-machine applications.
- Knowledge Logto production routing uses `https://knowledge-logto.orbitalis.org` for the auth endpoint and `https://admin.knowledge-logto.internal.home.arpa` for the admin console, both routed through the project-local `nginx` app gateway.
- Tracked environment files must carry the knowledge corpus, source pipeline, and taxonomy-classification queue-runtime fields alongside the online stack URL fields when those repository-managed app services are enabled.

## Failure Policy
- Known startup failures must fail explicitly and stop rollout progression.
- Silent fallback and partial startup in known invalid states are forbidden.
- Error details must remain observable in logs for debugging.
- Ingestion enqueue failures are logged and observable while accepted-ingestion response semantics remain unchanged.

## Deferred to Later Phases
- Backup and restore strategy definition.
- Replication, failover, and multi-node PostgreSQL topology.
- Platform-specific deployment targets beyond Docker Compose baseline.
