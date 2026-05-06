---
abstract: API-owned read-model cache design for high-concurrency public Search, MCP Search, and Graph View reads.
out_of_scope: Redis service topology, frontend query caching, MCP quota state, and web session storage.
---

# Design: api-read-model-cache

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the API-owned read-model cache boundary for public high-concurrency reads that reach the private API through the web BFF or public MCP service.
- **Scope/Boundaries:** Covers cache ownership, cacheable read surfaces, key construction, TTL policy, stale-read semantics, cache failure behavior, durable taxonomy layout read models, operator precompute orchestration, configuration, and validation expectations for Search, MCP Search, and Graph View read paths. Excludes Redis deployment topology, web session storage, MCP quota counters, and frontend TanStack Query behavior.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Public web and MCP reads must continue to enter through designated public surfaces, private API integration must remain contract-driven, module boundaries must remain explicit, and behavior-changing read-path decisions must stay synchronized in active specs.
- **Detail Commitments:** The private API owns shared read-model caches for public Search and Graph View reads. Web and MCP runtimes do not duplicate Search or Graph View response caches; they benefit by calling the private API. PostgreSQL remains authoritative for knowledge graph, taxonomy truth, and durable taxonomy card-scope layout read models. Redis stores short-TTL Search/taxonomy response caches and hot taxonomy layout payloads that can be recovered from PostgreSQL.
- **Update Rule:** Requirement-level public/private, module-boundary, and reproducibility constraints remain stable while cacheable surfaces, TTLs, key shape, payload validation, and failure behavior stay in this design document.

## Design Approach
- **Approach:** Use an API-local read-model cache boundary backed by Redis for hot reads and PostgreSQL for durable card-scope layout read models. Feature modules define their own cache keys, payload models, durability boundary, TTL policy, and validation rules. Shared cache infrastructure provides JSON get/set behavior, payload validation hooks, and fail-soft dependency behavior without owning feature semantics.
- **Key Elements:**
  - **API ownership:** `apps/api` owns read-model caches for private API responses used by public Search, MCP Search, and Graph View.
  - **Authoritative source:** PostgreSQL and external embedding providers remain the source of truth. Redis cache entries are derived data and may expire or be flushed without data loss. Full taxonomy card-scope layouts are durable PostgreSQL read models with Redis hot-cache entries.
  - **Public surface coverage:** Browser Search and MCP Search share the private API Search cache because both flows reach `GET /api/v1/search`. Graph View browser reads share taxonomy view caches because the web BFF forwards taxonomy view requests to private taxonomy endpoints.
  - **No BFF response cache:** The web BFF continues to own sessions, quota, Logto orchestration, and browser contracts. It does not own Search or Graph View response caches.
  - **No MCP response cache:** The MCP service continues to own protocol handling, PAT authentication, quota, usage, and analytics. It does not own Search response caching.
  - **Reusable cache boundary:** Shared API cache infrastructure is a technical concern only. It must not import feature modules or contain Search or taxonomy business logic.
  - **Feature-owned keys:** Search and taxonomy modules own cache key construction, cache schema versions, payload validation, and TTL constants or settings.
  - **Short TTL consistency:** Public Search, root taxonomy, and branch taxonomy read responses may be temporarily stale within the configured TTL window. Writes leave those cache entries to expire by TTL, and cache schema or algorithm changes use versioned keys.
  - **Layout validity identity:** Full taxonomy card-scope layouts are valid by layout algorithm version plus input fingerprint rather than by wall-clock age.
  - **Fail-soft reads:** Redis read, write, decode, or validation failures do not fail public read requests that can be served through bounded authoritative read flow. The API logs the cache failure, treats it as a cache miss, and returns data from authoritative dependencies when those dependencies succeed.
  - **Card-scope layout readiness:** Full layout read models are required for taxonomy card-scope metadata and viewport layout responses. Missing durable layout read models return `503 layout_not_ready` with `Retry-After` after one PostgreSQL-backed compute request is registered for the scope/version/input fingerprint. Stale durable layout read models are returned with a refreshing status while a single background compute refresh is registered.
  - **Request-path compute boundary:** Taxonomy card-scope layout simulation is long-running CPU-bound work and does not run inside API request handlers. The dedicated taxonomy view layout runtime consumes pending compute requests and writes full layout read models.
  - **Operator precompute boundary:** Card-scope layout precomputation is an operator workflow that enumerates currently valid card-scope scopes, registers missing or stale layout compute work through the taxonomy-owned compute request pipeline, and optionally drains that work through the same runtime processing unit used by the long-running taxonomy view layout runtime.
  - **Payload validation:** Cached JSON payloads must be validated through Pydantic models or existing response contract models before being returned to callers.

## Cacheable Surfaces

### Search Response Cache
- Caches final `SearchResponse` payloads for `GET /api/v1/search`.
- Cache key inputs include normalized query text, `search_algorithm_version`, `search_max_matched`, `search_max_connected`, and response cache schema version.
- Normalized query text is derived by trimming, collapsing whitespace, and case-folding the submitted query.
- Cache key stores a hash of normalized inputs rather than raw query text.
- TTL is configured by `KNOWLEDGE_API_SEARCH_RESPONSE_CACHE_TTL_SECONDS` and defaults to `60` seconds.
- Cache hits return validated `SearchResponse` payloads without calling the embedding provider or knowledge graph read port.
- Cache misses run the existing Search flow and write the validated response payload after successful retrieval.

### Search Embedding Cache
- Caches query embedding vectors used by Search.
- Cache key inputs include normalized query text, embedding model, and embedding cache schema version.
- Cache key stores a hash of normalized inputs rather than raw query text.
- TTL is configured by `KNOWLEDGE_API_SEARCH_EMBEDDING_CACHE_TTL_SECONDS` and defaults to `86400` seconds.
- Cache hits avoid embedding-provider calls and continue through knowledge graph hybrid retrieval.
- Cache misses call the configured embedding provider and write the returned vector after payload validation.
- Embedding cache entries are intermediate read models and are not returned directly to public clients.

### Taxonomy View Response Cache
- Caches taxonomy root, branch node, and branch path view responses for Graph View.
- Cache key inputs include taxonomy view cache schema version plus one of:
  - root view identity
  - node id
  - hash of canonical route path
- TTL is configured by `KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS` and defaults to `60` seconds.
- Cache hits return validated taxonomy response payloads without reloading the taxonomy tree or recomputing response shaping.
- Cache misses run bounded taxonomy-owned read orchestration and write the validated branch response payload.
- Card-scope metadata responses are derived from the taxonomy-owned full layout read model and are not stored in the short-TTL taxonomy response cache, so layout freshness checks and refresh registration are not hidden behind response-cache hits.
- Taxonomy view response caches use short TTL consistency and versioned keys for payload-shape changes.

### Graph View Cache Surface Matrix
- `GET /api/v1/taxonomy/view/root`: cached as a validated taxonomy view response under `knowledge:api:taxonomy-view:v1:root` with a `60` second TTL.
- `GET /api/v1/taxonomy/view/nodes/{node_id}` for a branch node: cached as a validated taxonomy view response under `knowledge:api:taxonomy-view:v1:node:{node_id}` with a `60` second TTL.
- `GET /api/v1/taxonomy/view/nodes/{node_id}` for a real card-scope node: not stored in the short-TTL taxonomy response cache. It derives metadata from the taxonomy-owned full layout read model, returns `layout_status`, and registers refresh compute when the durable layout fingerprint is stale.
- `GET /api/v1/taxonomy/view/path/{route_path:path}`: cached only when it resolves to a branch response under `knowledge:api:taxonomy-view:v1:path:{route_path_hash}` with a `60` second TTL. Card-scope path responses are derived from the taxonomy-owned full layout read model.
- `GET /api/v1/taxonomy/view/card-scopes/layout`: the per-viewport response is not stored as an independent Redis response cache. It is derived from the taxonomy-owned full layout read model, returns `layout_status`, and returns `layout_not_ready` only when no durable layout exists for the scope.
- `POST /api/v1/taxonomy/view/card-scopes/titles`: not stored in Redis; callers fetch explicit node-id batches from authoritative read ports.
- `POST /api/v1/taxonomy/view/card-scopes/details`: not stored in Redis; callers fetch explicit node-id batches from authoritative read ports.

### Taxonomy Card-Scope Layout And Hydration Cache Policy
- Taxonomy descendant-count Redis cache and full card-scope layout durable read models are taxonomy-owned.
- Descendant counts use a `60` second TTL.
- Full card-scope layouts are stored durably in PostgreSQL by explicit scope identity, active layout algorithm version, input fingerprint, generated timestamp, and payload.
- Full card-scope layout Redis hot-cache keys include the active layout algorithm version and explicit scope identity. The cached value stores `input_fingerprint` with the layout payload, and hot-cache entries do not expire by layout TTL.
- Full layout payloads are required before card-scope metadata or viewport layout responses can be returned.
- Missing durable full layout entries return `503 layout_not_ready` with `Retry-After` after the API registers or refreshes a PostgreSQL-backed compute request keyed by card-scope identity, active layout version, and input fingerprint.
- Stale durable full layout entries return `200` with `layout_status = "refreshing"` while the API registers a single background compute request for the current input fingerprint.
- PostgreSQL compute request state prevents duplicate compute requests for concurrent callers targeting the same scope/version/input fingerprint.
- The API request path does not run the CPU-bound card-scope layout simulation.
- The taxonomy view layout runtime consumes pending PostgreSQL compute requests, runs the deterministic layout simulation, writes the durable full layout entry, refreshes the Redis hot cache, and records compute success or failure.
- The operator precompute workflow discovers card-scope targets using the same taxonomy service semantics that determine whether a route renders as a card-scope view. It covers all currently user-reachable card-scope scopes, including any virtual card-scope scopes produced by the taxonomy view service.
- The operator precompute workflow supports a queue-only mode that registers compute requests and exits after reporting queued, already-ready, refreshing, failed, and total target counts.
- The operator precompute workflow supports a wait mode that processes or observes pending compute work until the selected target set has durable ready layouts, a configured timeout is reached, or an unrecoverable error occurs.
- Wait mode supports bounded worker concurrency by running multiple existing runtime processing units against the same PostgreSQL compute request queue. The claim path remains responsible for singleflight behavior. The operator wrapper applies a precompute-only Compose resource override so the one-off runtime has a higher CPU quota than the long-running background runtime.
- Operator precompute work uses the existing durable compute request table, layout input fingerprint, layout version, runtime claim/complete/fail semantics, PostgreSQL layout read model, and Redis hot-cache write path. It does not write layout payloads through a separate persistence path.
- Operator precompute output is machine-readable enough for automation and human-readable enough for release readiness checks. It reports per-scope failures with route path, scope identity, status, and error text. Interactive wait runs emit progress counts without corrupting final JSON stdout.
- Viewport layout slices are derived from cached full layouts and are not stored as independent Redis response caches.
- Card-scope title and detail requests are not stored in Redis; frontend local/TanStack caches handle immediate repeated browser hydration.

## Key Namespace
- API read-model cache keys use the `knowledge:api:` prefix.
- Search response keys use `knowledge:api:search-response:v1:{hash}`.
- Search embedding keys use `knowledge:api:search-embedding:v1:{embedding_model}:{hash}`.
- Taxonomy view response keys use:
  - `knowledge:api:taxonomy-view:v1:root`
  - `knowledge:api:taxonomy-view:v1:node:{node_id}`
  - `knowledge:api:taxonomy-view:v1:path:{route_path_hash}`
- Taxonomy descendant-count and full card-scope layout hot-cache keys use taxonomy-owned key namespaces.
- Taxonomy card-scope layout hot-cache keys are stable per scope/version; values include `input_fingerprint` so the API can return stale payloads as `refreshing` until the replacement layout overwrites the hot cache.
- Feature modules may bump the cache schema version when payload shape or key semantics change.

## Runtime Composition
- API runtime composition uses `Settings.redis_url` as the only Redis connection source for read-model caches.
- Search and taxonomy response cache TTL settings live in API settings and environment templates.
- Taxonomy card-scope layout hot-cache entries do not have a layout TTL setting.
- Provider wiring injects cache ports into Search and taxonomy services at the API composition root.
- Feature services remain testable without Redis by accepting optional cache ports or test doubles.
- Operator precompute composition uses the same database, Redis, taxonomy repo, taxonomy service, and knowledge projection service wiring as the taxonomy view layout runtime. It runs as an explicit operator command rather than as a public HTTP endpoint. The local wrapper requires an explicit environment selection for production and maps `dev` to the development Compose overlay and `prod` to the production Compose overlay. Production one-off precompute runs do not start Compose dependencies; they expect the production stack to already be running.
- Operator precompute wait mode may process compute work in-process by calling the runtime processing unit, or it may observe an already-running taxonomy view layout runtime, but both modes must respect the same compute request state machine and must not start duplicate work for the same scope/version/input fingerprint.

## Failure Behavior
- Missing keys are cache misses.
- Expired short-TTL response keys are cache misses.
- Redis connection, timeout, command, decode, or validation errors are logged and handled as cache misses.
- Cache set failures are logged and do not change the response returned to callers.
- Malformed cache entries are not returned. The API may delete or overwrite malformed entries after recomputing the read model.
- Card-scope layout hot-cache misses fall back to durable PostgreSQL layout reads.
- Card-scope layout durable misses are readiness failures, not request-path recomputation triggers. The API returns `503 layout_not_ready` after registering one compute request for the scope/version/input fingerprint.
- Card-scope layout stale durable hits are served with a refreshing status and a compute request for the current input fingerprint.
- Redis dependency failures in the card-scope layout readiness path do not fail requests that can be served from durable PostgreSQL layouts.
- Authoritative dependency failures still surface through existing error-governance behavior.
- Operator precompute failures are visible operator failures. The command exits non-zero when target discovery fails, compute registration fails, wait mode times out before all selected targets are ready, or any selected target remains failed at completion.
- Operator precompute does not mask failed scope computations as successful warmup. Failed scopes remain inspectable through the compute request state and are reported in command output.
- Queue-only mode may exit successfully after registering work even when compute has not completed, but it must label the result as queued rather than ready.

## Validation
- Search cache tests verify response cache hits bypass the embedding provider and knowledge graph read port.
- Search cache tests verify embedding cache hits bypass the embedding provider while preserving hybrid retrieval behavior.
- Search cache tests verify cache misses write response and embedding entries with configured TTLs.
- Search cache tests verify malformed cached payloads and Redis failures fall back to authoritative read flow.
- Search key tests verify normalized query, limits, embedding model, and algorithm/cache versions affect keys as specified.
- Taxonomy cache tests verify root, branch node, and branch path view cache hits return validated payloads.
- Taxonomy cache tests verify miss, malformed payload, and Redis failure behavior.
- Taxonomy service and repository tests verify missing durable full card-scope layout read models return `503 layout_not_ready` with `Retry-After` and register at most one compute request for concurrent callers.
- Taxonomy service tests verify stale durable full card-scope layout read models return data with `layout_status = "refreshing"` and register a background refresh request.
- Taxonomy cache tests verify card-scope metadata and viewport layout request handlers do not run the CPU-bound layout simulation on cache miss.
- Taxonomy runtime tests verify the taxonomy view layout runtime consumes pending PostgreSQL compute requests and writes durable full layout read models plus Redis hot-cache entries.
- Taxonomy operator tests verify precompute target discovery uses the same card-scope semantics as taxonomy view responses and includes virtual card-scope scopes when they are user-reachable.
- Taxonomy operator tests verify queue-only precompute registers compute requests without building layouts directly.
- Taxonomy operator tests verify wait-mode precompute uses the runtime processing path, reports ready and failed target counts, and exits non-zero on timeout or failed selected targets.
- Settings tests verify API cache TTL settings parse from environment and do not include a taxonomy card-scope layout TTL.
- Provider tests verify cache wiring uses `Settings.redis_url` and does not read Redis configuration from scattered environment variables.
- Contract drift checks remain unchanged because cache behavior preserves public and private API response contracts.
