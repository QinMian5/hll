---
abstract: Module-level orchestration design for knowledge core ownership, card versions, suggested-edit submission, ingestion async write pipeline, cache-backed hybrid search read flow, and taxonomy drill-down reads.
out_of_scope: LLM reranking, cross-encoder reranking, suggestion review UI, ingestion status APIs, and distributed multi-region queue reliability.
---

# Design: knowledge-ingestion-search-orchestration

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.

## Context
- **Purpose:** Define accepted V1 orchestration for `knowledge_graph`, `taxonomy`, `taxonomy_classification`, `ingestion`, `search`, and card suggestion submission under async ingestion with Redis/Dramatiq and API-owned read-model caches.
- **Scope/Boundaries:** Covers module ownership, endpoint contracts, async processing flow, card version/suggestion submission rules, taxonomy bootstrap/classification boundaries, taxonomy drill-down read rules, cache-backed Search orchestration, and runtime observability obligations.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Module Ownership

### knowledge_graph
- Owns persistent domain truth for `Node`, `CardVersion`, `CardSuggestedEdit`, `Edge`, and `Adjacency`.
- Is the only module allowed to own/access graph persistence models and repositories.
- Exposes read/write service ports consumed by `search`, `ingestion`, and `taxonomy`.
- Exposes suggested-edit creation ports consumed by private API orchestration.

### taxonomy
- Owns persisted operator-managed LCC taxonomy tree and current direct node-to-taxonomy assignment truth.
- Owns the real single `Root` node and path-addressed virtual Unclassified view scopes.
- Owns taxonomy import and operator structure mutation orchestration.
- Owns default assignment of new knowledge nodes directly to `Root`.
- Owns assignment movement between valid real taxonomy nodes.
- Owns taxonomy drill-down read orchestration:
  - `GET /api/v1/taxonomy/view/root`
  - `GET /api/v1/taxonomy/view/nodes/{node_id}`
  - `GET /api/v1/taxonomy/view/path/{route_path:path}`
  - `GET /api/v1/taxonomy/view/card-scopes/layout`
  - `POST /api/v1/taxonomy/view/card-scopes/titles`
  - `POST /api/v1/taxonomy/view/card-scopes/details`
- Consumes `knowledge_graph` read ports for card-scope layout, title, and detail payload shaping.

### taxonomy_classification
- Owns operator-triggered `taxonomy_classification` queue job submission for cards directly assigned to selected taxonomy scopes.
- Owns background result consumption through notification-only webhooks plus lightweight polling/reconcile.
- Submits one `job-queue-mcp` job per selected card.
- Consumes `knowledge_graph` and `taxonomy` service ports only.
- Applies valid accepted classification results by moving assignments through taxonomy-owned services.

### ingestion
- Owns write-side HTTP acceptance endpoint and async dispatch orchestration.
- Records each newly accepted request in `ingestion_requests` before queue dispatch.
- Returns `202 Accepted` only after the accepted request has an integer database id and the queue message has been published.
- Owns ingestion-scoped queue broker configuration and publish adapter (Redis + Dramatiq).
- Worker path persists node/edge truth through `knowledge_graph` write service.

### search
- Owns read-side search endpoint and orchestration.
- Resolves cache-backed Search responses and query embeddings before requesting balanced hybrid retrieval through `knowledge_graph` read service.
- Preserves the private search response contract while delegating vector, lexical, and rank-fusion primitives to `knowledge_graph`.
- Follows the API read-model cache policy defined in `api-read-model-cache.md`.

## API Contract

### Ingestion Endpoint
- Route: `POST /api/v1/cards`
- Request fields: `title`, `content`
- Optional request header: `Idempotency-Key`
- Response:
  - invalid payload: `4xx` via global error-governance mapping
  - repeated `Idempotency-Key` with conflicting payload: `409 Conflict`
  - queue unavailable before accepted-request completion: `503 Service Unavailable`
  - valid first submission: `202 Accepted`
  - repeated `Idempotency-Key` with identical payload: `202 Accepted`
  - accepted response body includes `accepted: true` and integer `ingestion_id`
- Idempotency behavior:
  - requests with the same non-empty `Idempotency-Key` and same card payload are treated as the same logical accepted submission
  - repeated accepted submissions for the same idempotency key and same card payload must return `202 Accepted` with the original integer `ingestion_id` without enqueueing duplicate ingestion work or materializing duplicate knowledge cards
  - repeated idempotency keys with different card payloads are rejected with `409 Conflict`
  - requests without a non-empty `Idempotency-Key` always allocate independent integer `ingestion_id` values
  - idempotency get-or-create is repository-owned and database-atomic; service code must not implement a separate check-then-insert sequence

### Search Endpoint
- Route: `GET /api/v1/search?query=<string>`
- Response:
  - `matched_cards` with `node_id`, `current_version`, `title`, `content`
  - `connected_titles`
- Cache behavior:
  - API-owned Redis read-model caches may serve validated Search responses for normalized repeated queries.
  - API-owned Redis embedding caches may serve normalized query embeddings before hybrid retrieval.
  - Cache entries are recomputable and may be temporarily stale within the configured TTL window.
  - Cache details are governed by `api-read-model-cache.md`.
- Ranking:
  - query embedding retrieves semantic vector candidates from `Node.embedding`
  - PostgreSQL full-text search retrieves lexical candidates from weighted `Node.title` and `Node.content`
  - title text carries higher lexical weight than content text
  - fused ranking uses reciprocal-rank fusion over vector and lexical candidate ranks
  - deterministic title-match boosts favor exact title matches, title phrase matches, and title all-token matches ahead of content-only lexical matches
  - embedding candidates remain eligible so natural-language questions and synonym-style queries can surface relevant cards even when exact terms are absent
- Limits:
  - `matched_cards` count is bounded by environment variable `KNOWLEDGE_API_SEARCH_MAX_MATCHED`
  - `connected_titles` count is bounded by environment variable `KNOWLEDGE_API_SEARCH_MAX_CONNECTED`

### Card Suggested Edit Endpoint
- Route: `POST /api/v1/cards/{node_id}/suggested-edits`
- Request fields:
  - `base_version`
  - `suggested_title`
  - `suggested_content`
  - `suggested_by_user_id`
- Response:
  - valid authenticated BFF-originated submission: `201 Created`
  - unknown card, unknown base version, invalid proposed values, or no-op suggestion: `4xx` via global error-governance mapping
- Response fields:
  - `id`
  - `node_id`
  - `base_version`
  - `status`
  - `created_at`
- Rules:
  - `suggested_by_user_id` is a Logto user id supplied by the BFF from the authenticated server-side session.
  - `(node_id, base_version)` must identify an existing formal card version.
  - proposed title/content must differ from the referenced base version.
  - a stale but existing `base_version` is accepted as the user's visible editing baseline.
  - created suggestions have status `pending`.

### Taxonomy Root View Endpoint
- Route: `GET /api/v1/taxonomy/view/root`
- Response:
  - no `current_scope` field
  - `breadcrumb=[]`
  - `children[]` visible direct child scopes of the real `Root`
  - child item shape includes explicit `scope_kind`, path identity, display fields, `node_kind`, and `descendant_card_count`
  - children ordering: `name ASC`, tie-break `id ASC`
- Failure:
  - `404` when the real `Root` node is unavailable.

### Taxonomy Node View Endpoint
- Route: `GET /api/v1/taxonomy/view/nodes/{node_id}`
- Response:
  - common envelope:
    - `node_kind` with value `branch` or `card_scope`
    - `current_scope` with explicit real taxonomy scope identity
    - `breadcrumb[]` ordered root-to-current with explicit real taxonomy scope identity
  - branch payload includes visible `children[]` direct child scopes
  - card-scope metadata payload includes `layout_version`, `world_bounds`, `node_count`, `edge_count`, and `generated_at`
  - card-scope metadata payload excludes full graph nodes, graph edges, node titles, node content, and `current_version`
- Failure:
  - `404` when taxonomy node id is unknown.
  - `404` when taxonomy root is unavailable.

### Taxonomy Path View Endpoint
- Route: `GET /api/v1/taxonomy/view/path/{route_path:path}`
- Request:
  - `route_path` is a slash-joined canonical LCC slug path excluding the system `Root` segment.
  - appending `/unclassified` addresses a visible virtual Unclassified card scope below the parent taxonomy route path.
- Response:
  - same response union as `GET /api/v1/taxonomy/view/nodes/{node_id}` for real taxonomy nodes
  - card-scope metadata payload for resolved virtual Unclassified scopes
  - response nodes include `route_slug` and `route_path`
- Failure:
  - `404` when any path segment does not resolve below its current parent.
  - `404` when an `unclassified` segment does not resolve to a visible virtual Unclassified scope.
  - `404` when taxonomy root is unavailable.

### Taxonomy Card-Scope Layout Viewport Endpoint
- Route: `GET /api/v1/taxonomy/view/card-scopes/layout`
- Request:
  - `route_path`
  - `min_x`, `min_y`, `max_x`, and `max_y` world-bound query parameters
- Response:
  - explicit scope identity and `route_path`
  - `layout_version`
  - `requested_bounds`
  - `nodes[]` ordered by `id ASC`; each item has `id`, `scope`, `x`, and `y`
  - `edges[]` ordered by `(source_node_id ASC, target_node_id ASC)`; each item is `[source_node_id, target_node_id, strength]`
- Failure:
  - `404` when `route_path` does not resolve to a card scope.
  - `404` when taxonomy root is unavailable.

### Taxonomy Card-Scope Titles Endpoint
- Route: `POST /api/v1/taxonomy/view/card-scopes/titles`
- Request:
  - `route_path`
  - `node_ids[]` non-empty array of unique positive integers scoped to the active card-scope one-hop graph
- Response:
  - `nodes[]` ordered to match requested `node_ids`
  - node title item shape: `{id, title}`
- Failure:
  - `404` when `route_path` does not resolve to a card scope
  - `404` when taxonomy root is unavailable
  - `400` when request `node_ids` is empty, contains duplicates, or references a node outside the active card-scope one-hop graph

### Taxonomy Card-Scope Detail Endpoint
- Route: `POST /api/v1/taxonomy/view/card-scopes/details`
- Request:
  - `route_path`
  - `node_ids[]` non-empty array of unique positive integers scoped to the active card-scope one-hop graph
- Response:
  - `nodes[]` ordered to match requested `node_ids`
  - node detail item shape: `{id, current_version, title, content}`
- Failure:
  - `404` when `route_path` does not resolve to a card scope
  - `404` when taxonomy root is unavailable
  - `400` when request `node_ids` is empty, contains duplicates, or references a node outside the active card-scope one-hop graph

## Async Processing Flow
1. API validates ingestion request payload.
2. API returns `4xx` for invalid payload.
3. API computes a stable payload hash from normalized card title and content.
4. API resolves the accepted request through repository-owned atomic get-or-create semantics.
5. API inserts a new `ingestion_requests` row for each first accepted submission and uses the database-assigned integer row id as `ingestion_id`.
6. API publishes a typed ingestion-task payload through ingestion-owned publisher adapter only for newly accepted submissions.
7. API rolls back the accepted-request row and returns `503` if queue publish fails before request acceptance completes.
8. API returns `202` for valid accepted payloads after publish succeeds.
9. Worker actor receives task and requests embedding from OpenAI Embeddings API (`text-embedding-3-small`).
10. Worker persists node truth through `knowledge_graph` write service.
11. Worker persists the node's formal initial card version and current version projection through `knowledge_graph` write service.
12. Worker assigns the new node directly to `Root` through taxonomy-owned assignment services.
13. Worker builds title-mention edge candidates from existing card titles that are complete normalized phrase matches inside the new card content.
14. Worker ranks title-mention candidates by embedding similarity descending and node id ascending, then persists at most the configured title-mention edge budget.
15. Worker builds semantic edge candidates from embedding similarity, bounded by the configured semantic candidate limit.
16. Worker removes nodes already selected through title-mention matching, applies the configured semantic strength threshold, ranks by similarity descending and node id ascending, then persists at most the configured semantic edge budget.
17. Worker computes persisted edge strength as `(dot_product + 1) / 2` for selected candidates.
18. Worker persists selected `Edge` and `Adjacency` rows.

## Edge Initialization
- Edge initialization is performed only on the ingestion write path.
- Title-mention candidates are existing nodes whose normalized title appears as a complete normalized phrase in the new card content.
- Title-mention candidate ordering is embedding similarity descending, then node id ascending.
- The title-mention edge count is bounded by `KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K`.
- Semantic candidates are retrieved by embedding similarity with a candidate pool bounded by `KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT`.
- Semantic candidates already selected by title mention are excluded from semantic edge selection.
- Semantic candidates must meet `KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH`.
- Semantic candidate ordering is embedding similarity descending, then node id ascending.
- The semantic edge count is bounded by `KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K`.
- Edge budget configuration is runtime-owned and may be adjusted without changing the domain model.
- Edge selection preserves the existing canonical unordered-pair storage rule.

## Card Version Rollout Invariant
- New ingested nodes create `nodes.current_version = 1` and `card_versions(version = 1)` in the same write path.
- Existing nodes must be backfilled to the same invariant before authenticated suggested-edit submission is enabled, so every submitted `(node_id, base_version)` can reference `card_versions(node_id, version)`.

## Taxonomy Bootstrap Flow
1. Operator script creates or imports one authoritative tree rooted at the real `Root` node.
2. Creating a taxonomy node creates only the requested real LCC category node.
3. Taxonomy storage remains the authoritative structure truth.

## Taxonomy Classification Flow
1. Operator script resolves one scope by case-insensitive name or path, or scans all eligible directly assigned scopes.
2. Operator script selects cards directly assigned to each selected scope in deterministic order (`nodes.id ASC` within each scope).
3. Operator script skips selected scopes that have no regular direct child categories.
4. Operator script submits one `taxonomy_classification` queue job per selected card.
5. `job-queue-mcp` delivers notification-only events for accepted results and terminal non-accepted outcomes.
6. The local taxonomy-classification runtime persists webhook events idempotently and reads accepted result payloads through batch result-read requests.
7. Valid child targets move the card assignment directly to the selected child category.
8. Valid `unclassified` targets keep the card assignment at the current scope.
9. Invalid accepted results and terminal non-accepted outcomes record local processing state without moving assignments.
10. Lightweight polling/reconcile checks outstanding job links as a compensation path.

## Runtime Dependencies
- Redis is required for ingestion queue broker transport.
- Dramatiq is required for async worker execution.
- API and worker run in separate process containers from one shared app image.
- `job-queue-mcp` is required for taxonomy classification queue execution and result reads.
- OpenAI Embeddings API is required for worker ingestion and search query embedding.
- PostgreSQL full-text search is required for lexical card retrieval and ranking.
- PostgreSQL remains persistent source of truth.
- Runtime configuration values are sourced from `.env` via `pydantic-settings`.
- Edge initialization configuration is sourced from `KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K`, `KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K`, `KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH`, and `KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT`.

## Failure Handling
- Invalid request payloads are client-visible as `4xx`.
- Enqueue/worker/embedding/materialization failures for ingestion remain internal-only for endpoint behavior.
- Internal failures must be logged with correlation/debug-friendly fields.
- Taxonomy view endpoints expose backend-owned card-scope layout coordinates only through the viewport-bounded card-scope layout endpoint.
- Taxonomy classification workers do not write knowledge APIs or databases.
- Taxonomy classification result processing moves assignments only after local validation against current taxonomy truth.

## Non-Goals (V1)
- Semantic-map snapshot/tile APIs.
- LLM or cross-encoder search reranking.
- Ingestion processing-status exposure.
- Dead-letter queue policy matrix and queue durability optimization.
- HTTP-triggered taxonomy classification management APIs.

## Validation
- **Checks:**
  - `POST /api/v1/cards` contract checks (`4xx` invalid, `202` valid)
  - ingestion response-contract checks verifying `ingestion_id` is an integer
  - ingestion request checks verifying submissions without a non-empty `Idempotency-Key` still allocate independent database ids
  - ingestion idempotency checks verifying first same-key submission publishes once and returns `202 Accepted`
  - ingestion idempotency checks verifying same-key same-payload replay returns `202 Accepted` without enqueueing duplicate ingestion work or materializing duplicate knowledge cards
  - ingestion idempotency checks verifying same-key conflicting payload returns `409 Conflict`
  - ingestion idempotency checks verifying timeout or connection-loss retry after an already accepted original request converges through same-key replay
  - ingestion queue-failure checks verifying failed publish before accepted-request completion returns `503` and rolls back the accepted-request row
  - ingestion worker checks verifying newly created nodes receive direct `Root` assignment
  - ingestion edge-initialization checks verifying title-mention edge selection respects the configured title-mention budget
  - ingestion edge-initialization checks verifying title-mention candidates are ordered by embedding similarity with stable node-id tie-breaking
  - ingestion edge-initialization checks verifying semantic edge selection respects the configured semantic candidate limit and semantic edge budget
  - ingestion edge-initialization checks verifying semantic edge selection excludes nodes already selected through title mention
  - configuration checks verifying edge initialization settings are accepted as runtime policy and are not hard-coded into algorithm tests
  - `GET /api/v1/search` contract checks
  - search ranking checks verifying exact-title and title-token lexical matches rank ahead of content-only matches
  - search ranking checks verifying semantic vector candidates remain eligible when lexical matches are absent
  - search ranking checks verifying reciprocal-rank fusion produces deterministic ordering and tie-breaking
  - `POST /api/v1/cards/{node_id}/suggested-edits` contract checks
  - suggested-edit checks verifying valid base-version submissions create pending suggestions
  - suggested-edit checks verifying unknown base versions, empty proposed values, and no-op suggestions are rejected
  - suggested-edit checks verifying stale but existing base versions are accepted
  - `GET /api/v1/taxonomy/view/root`, `GET /api/v1/taxonomy/view/nodes/{id}`, `GET /api/v1/taxonomy/view/path/{route_path:path}`, `GET /api/v1/taxonomy/view/card-scopes/layout`, `POST /api/v1/taxonomy/view/card-scopes/titles`, and `POST /api/v1/taxonomy/view/card-scopes/details` contract checks
  - taxonomy classification queue-contract checks
  - taxonomy classification webhook/reconcile checks
  - taxonomy classification assignment-move checks
  - architecture checks that `search`/`ingestion` do not import `knowledge_graph.repo/model`
  - architecture checks that runtime API entrypoint does not import worker entrypoint
- **Evidence:**
  - passing API/worker integration tests and boundary checks
  - logs showing internal observability for async failure paths
