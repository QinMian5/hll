---
abstract: API-owned Redis read-model cache design for high-concurrency public Search, MCP Search, and Graph View reads.
out_of_scope: Redis service topology, durable persistence, frontend query caching, MCP quota state, and web session storage.
---

# Design: api-read-model-cache

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the API-owned Redis read-model cache boundary for public high-concurrency reads that reach the private API through the web BFF or public MCP service.
- **Scope/Boundaries:** Covers cache ownership, cacheable read surfaces, key construction, TTL policy, stale-read semantics, cache failure behavior, configuration, and validation expectations for Search, MCP Search, and Graph View read paths. Excludes Redis deployment topology, queue broker semantics, web session storage, MCP quota counters, and frontend TanStack Query behavior.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Public web and MCP reads must continue to enter through designated public surfaces, private API integration must remain contract-driven, module boundaries must remain explicit, and behavior-changing read-path decisions must stay synchronized in active specs.
- **Detail Commitments:** The private API owns shared Redis read-model caches for public Search and Graph View reads. Web and MCP runtimes do not duplicate Search or Graph View response caches; they benefit by calling the private API. PostgreSQL remains authoritative for knowledge graph and taxonomy truth. Redis stores only recomputable read responses and intermediate read models with short TTLs.
- **Update Rule:** Requirement-level public/private, module-boundary, and reproducibility constraints remain stable while cacheable surfaces, TTLs, key shape, payload validation, and failure behavior stay in this design document.

## Design Approach
- **Approach:** Use an API-local read-model cache boundary backed by Redis. Feature modules define their own cache keys, payload models, and TTLs. Shared cache infrastructure provides JSON get/set behavior, TTL application, payload validation hooks, and fail-soft dependency behavior without owning feature semantics.
- **Key Elements:**
  - **API ownership:** `apps/api` owns read-model caches for private API responses used by public Search, MCP Search, and Graph View.
  - **Authoritative source:** PostgreSQL and external embedding providers remain the source of truth. Redis cache entries are derived data and may expire or be flushed without data loss.
  - **Public surface coverage:** Browser Search and MCP Search share the private API Search cache because both flows reach `GET /api/v1/search`. Graph View browser reads share taxonomy view caches because the web BFF forwards taxonomy view requests to private taxonomy endpoints.
  - **No BFF response cache:** The web BFF continues to own sessions, quota, Logto orchestration, and browser contracts. It does not own Search or Graph View response caches.
  - **No MCP response cache:** The MCP service continues to own protocol handling, PAT authentication, quota, usage, and analytics. It does not own Search response caching.
  - **Reusable cache boundary:** Shared API cache infrastructure is a technical concern only. It must not import feature modules or contain Search or taxonomy business logic.
  - **Feature-owned keys:** Search and taxonomy modules own cache key construction, cache schema versions, payload validation, and TTL constants or settings.
  - **Short TTL consistency:** Public read responses may be temporarily stale within the configured TTL window. Writes leave cache entries to expire by TTL, and cache schema or algorithm changes use versioned keys.
  - **Fail-soft reads:** Redis read, write, decode, or validation failures do not fail successful public read requests. The API logs the cache failure, treats it as a cache miss, and returns data from authoritative dependencies when those dependencies succeed.
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
- Caches taxonomy root, branch node, leaf metadata, and canonical path view responses for Graph View.
- Cache key inputs include taxonomy view cache schema version plus one of:
  - root view identity
  - node id
  - hash of canonical route path
- TTL is configured by `KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS` and defaults to `60` seconds.
- Cache hits return validated taxonomy response payloads without reloading the taxonomy tree or recomputing response shaping.
- Cache misses run taxonomy-owned read orchestration and write the validated response payload.
- Taxonomy view response caches use short TTL consistency and versioned keys for payload-shape changes.

### Graph View Cache Surface Matrix
- `GET /api/v1/taxonomy/view/root`: cached as a validated taxonomy view response under `knowledge:api:taxonomy-view:v1:root` with a `60` second TTL.
- `GET /api/v1/taxonomy/view/nodes/{node_id}` for a branch node: cached as a validated taxonomy view response under `knowledge:api:taxonomy-view:v1:node:{node_id}` with a `60` second TTL.
- `GET /api/v1/taxonomy/view/nodes/{node_id}` for a leaf node: cached as validated leaf metadata under `knowledge:api:taxonomy-view:v1:node:{node_id}` with a `60` second TTL. The cached metadata excludes full graph nodes, graph edges, node titles, node content, and `current_version`.
- `GET /api/v1/taxonomy/view/path/{route_path:path}`: cached as the resolved branch or leaf metadata response under `knowledge:api:taxonomy-view:v1:path:{route_path_hash}` with a `60` second TTL.
- `GET /api/v1/taxonomy/view/leaves/{node_id}/layout`: the per-viewport response is not stored as an independent Redis response cache. It is derived from the taxonomy-owned full leaf layout read model.
- `POST /api/v1/taxonomy/view/leaves/{node_id}/titles`: not stored in Redis; callers fetch explicit node-id batches from authoritative read ports.
- `POST /api/v1/taxonomy/view/leaves/{node_id}/details`: not stored in Redis; callers fetch explicit node-id batches from authoritative read ports.

### Taxonomy Leaf Layout And Hydration Cache Policy
- Taxonomy descendant-count and full leaf-layout Redis caches are taxonomy-owned read models.
- Descendant counts use a `60` second TTL.
- Full leaf layouts use a `600` second TTL and include the active leaf layout algorithm version in their cache key.
- Full leaf-layout cache entries expire by TTL and use versioned keys for layout-shape changes.
- Viewport layout slices are derived from cached full leaf layouts and are not stored as independent Redis response caches.
- Leaf title and detail requests are not stored in Redis; frontend local/TanStack caches handle immediate repeated browser hydration.

## Key Namespace
- API read-model cache keys use the `knowledge:api:` prefix.
- Search response keys use `knowledge:api:search-response:v1:{hash}`.
- Search embedding keys use `knowledge:api:search-embedding:v1:{embedding_model}:{hash}`.
- Taxonomy view response keys use:
  - `knowledge:api:taxonomy-view:v1:root`
  - `knowledge:api:taxonomy-view:v1:node:{node_id}`
  - `knowledge:api:taxonomy-view:v1:path:{route_path_hash}`
- Taxonomy descendant-count and full leaf-layout read-model keys use taxonomy-owned key namespaces.
- Feature modules may bump the cache schema version when payload shape or key semantics change.

## Runtime Composition
- API runtime composition uses `Settings.redis_url` as the only Redis connection source for read-model caches.
- Cache TTL settings live in API settings and environment templates.
- Provider wiring injects cache ports into Search and taxonomy services at the API composition root.
- Feature services remain testable without Redis by accepting optional cache ports or test doubles.

## Failure Behavior
- Missing keys are cache misses.
- Expired keys are cache misses.
- Redis connection, timeout, command, decode, or validation errors are logged and handled as cache misses.
- Cache set failures are logged and do not change the response returned to callers.
- Malformed cache entries are not returned. The API may delete or overwrite malformed entries after recomputing the read model.
- Authoritative dependency failures still surface through existing error-governance behavior.

## Validation
- Search cache tests verify response cache hits bypass the embedding provider and knowledge graph read port.
- Search cache tests verify embedding cache hits bypass the embedding provider while preserving hybrid retrieval behavior.
- Search cache tests verify cache misses write response and embedding entries with configured TTLs.
- Search cache tests verify malformed cached payloads and Redis failures fall back to authoritative read flow.
- Search key tests verify normalized query, limits, embedding model, and algorithm/cache versions affect keys as specified.
- Taxonomy cache tests verify root, branch node, leaf metadata node, and path view cache hits return validated payloads.
- Taxonomy cache tests verify miss, malformed payload, and Redis failure behavior.
- Settings tests verify API cache TTL settings parse from environment and expose accepted defaults.
- Provider tests verify cache wiring uses `Settings.redis_url` and does not read Redis configuration from scattered environment variables.
- Contract drift checks remain unchanged because cache behavior preserves public and private API response contracts.
