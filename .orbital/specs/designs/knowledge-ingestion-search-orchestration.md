---
abstract: Module-level orchestration design for knowledge core ownership, ingestion async write pipeline, cosine-only search read flow, and taxonomy drill-down reads.
out_of_scope: Keyword retrieval, hybrid reranking, ingestion status APIs, and distributed multi-region queue reliability.
---

# Design: knowledge-ingestion-search-orchestration

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.

## Context
- **Purpose:** Define accepted V1 orchestration for `knowledge_graph`, `taxonomy`, `taxonomy_classification`, `ingestion`, and `search` under async ingestion with Redis/Dramatiq.
- **Scope/Boundaries:** Covers module ownership, endpoint contracts, async processing flow, taxonomy bootstrap/classification boundaries, taxonomy drill-down read rules, and runtime observability obligations.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Module Ownership

### knowledge_graph
- Owns persistent domain truth for `Node`, `Edge`, and `Adjacency`.
- Is the only module allowed to own/access graph persistence models and repositories.
- Exposes read/write service ports consumed by `search`, `ingestion`, and `taxonomy`.

### taxonomy
- Owns persisted operator-managed taxonomy tree and current node-to-leaf assignment truth.
- Owns the real single `Root` node and system-created `Unclassified` leaves.
- Owns taxonomy import and operator structure mutation orchestration.
- Owns default assignment of new knowledge nodes to `Root -> Unclassified`.
- Owns assignment movement between valid taxonomy leaves.
- Owns taxonomy drill-down read orchestration:
  - `GET /api/v1/taxonomy/view/root`
  - `GET /api/v1/taxonomy/view/nodes/{node_id}`
  - `POST /api/v1/taxonomy/view/leaves/{node_id}/details`
- Consumes `knowledge_graph` read ports for leaf-level one-hop graph payload shaping.

### taxonomy_classification
- Owns operator-triggered `taxonomy_classification` queue job submission for cards in one scope node's `Unclassified` leaf.
- Owns background result consumption through notification-only webhooks plus lightweight polling/reconcile.
- Submits one `job-queue-mcp` job per selected card.
- Consumes `knowledge_graph` and `taxonomy` service ports only.
- Applies valid accepted classification results by moving assignments through taxonomy-owned services.

### ingestion
- Owns write-side HTTP acceptance endpoint and async dispatch orchestration.
- Accepts valid payloads and returns `202 Accepted`.
- Owns ingestion-scoped queue broker configuration and publish adapter (Redis + Dramatiq).
- Worker path persists node/edge truth through `knowledge_graph` write service.

### search
- Owns read-side search endpoint and orchestration.
- Uses cosine-only retrieval via `knowledge_graph` read service.

## API Contract

### Ingestion Endpoint
- Route: `POST /api/v1/cards`
- Request fields: `title`, `content`
- Optional request header: `Idempotency-Key`
- Response:
  - invalid payload: `4xx` via global error-governance mapping
  - repeated `Idempotency-Key` with conflicting payload: `409 Conflict`
  - valid first submission: `202 Accepted`
  - repeated `Idempotency-Key` with identical payload: `202 Accepted`
- Idempotency behavior:
  - requests with the same non-empty `Idempotency-Key` and same card payload are treated as the same logical accepted submission
  - repeated accepted submissions for the same idempotency key and same card payload must return `202 Accepted` without enqueueing duplicate ingestion work or materializing duplicate knowledge cards
  - repeated idempotency keys with different card payloads are rejected with `409 Conflict`

### Search Endpoint
- Route: `GET /api/v1/search?query=<string>`
- Response:
  - `matched_cards` with `title`, `content` only
  - `connected_titles`
- Limits:
  - `matched_cards` count is bounded by environment variable `KNOWLEDGE_API_SEARCH_MAX_MATCHED`
  - `connected_titles` count is bounded by environment variable `KNOWLEDGE_API_SEARCH_MAX_CONNECTED`

### Taxonomy Root View Endpoint
- Route: `GET /api/v1/taxonomy/view/root`
- Response:
  - no `current_node` field
  - `breadcrumb=[]`
  - `children[]` direct children of the real `Root` node
  - child item shape: `{id, parent_id, name, depth, is_leaf, descendant_card_count}`
  - children ordering: `name ASC`, tie-break `id ASC`
- Failure:
  - `404` when the real `Root` node is unavailable.

### Taxonomy Node View Endpoint
- Route: `GET /api/v1/taxonomy/view/nodes/{node_id}`
- Response:
  - common envelope:
    - `node_kind`
    - `current_node` `{id, parent_id, name, depth, is_leaf}`
    - `breadcrumb[]` ordered root-to-current with item shape `{id, parent_id, name, depth, is_leaf}`
  - branch payload (`children`) when node is non-leaf
  - leaf payload (`nodes`, `edges`) when node is leaf
- Leaf payload rules:
  - nodes include all leaf inner cards and all one-hop pulled outer cards
  - node fields are `id`, `scope`
  - edges are numeric tuples shaped as `[source_node_id, target_node_id, strength]`
  - canonical endpoint ordering is required for every edge: `source_node_id < target_node_id`
  - edges include only `inner-inner` and `inner-outer`
  - `outer-outer` edges are excluded
  - nodes are ordered `id ASC`
  - edges are deduplicated by undirected pair and ordered `(source_node_id ASC, target_node_id ASC)`
  - response is full payload, no pagination
- Failure:
  - `404` when taxonomy node id is unknown.
  - `404` when taxonomy root is unavailable.

### Taxonomy Leaf Detail Endpoint
- Route: `POST /api/v1/taxonomy/view/leaves/{node_id}/details`
- Request:
  - `node_ids[]` non-empty array of unique positive integers scoped to the active leaf one-hop graph
- Response:
  - `nodes[]` ordered to match requested `node_ids`
  - node detail item shape: `{id, title, content}`
- Failure:
  - `404` when taxonomy leaf id is unknown
  - `404` when taxonomy root is unavailable
  - `400` when `node_id` is not a leaf taxonomy node
  - `400` when request `node_ids` is empty, contains duplicates, or references a node outside the active leaf one-hop graph

## Async Processing Flow
1. API validates ingestion request payload.
2. API returns `4xx` for invalid payload.
3. API enforces idempotency when a non-empty `Idempotency-Key` header is present.
4. API publishes Dramatiq message through ingestion-owned publisher adapter for the first accepted submission of one idempotency key.
5. API returns `202` for valid payload.
6. Worker actor receives task and requests embedding from OpenAI Embeddings API (`text-embedding-3-small`).
7. Worker persists node and edges through `knowledge_graph` write service.
8. Worker computes edge strength as `(dot_product + 1) / 2`, applies configured threshold/top-k, then persists `Edge` and `Adjacency`.
9. Worker assigns the new node to `Root -> Unclassified` through taxonomy-owned assignment services.

## Taxonomy Bootstrap Flow
1. Operator script creates or imports one authoritative tree rooted at the real `Root` node.
2. Bootstrap creates `Root -> Unclassified`.
3. Creating a regular taxonomy node creates that node's `Unclassified` child leaf.
4. Taxonomy storage remains the authoritative structure truth.

## Taxonomy Classification Flow
1. Operator script selects cards assigned to one scope node's `Unclassified` leaf in deterministic order (`nodes.id ASC`).
2. Operator script submits one `taxonomy_classification` queue job per selected card.
3. `job-queue-mcp` delivers notification-only events for accepted results and terminal non-accepted outcomes.
4. The local taxonomy-classification runtime persists webhook events idempotently and reads accepted result payloads through `GET /results/{job_id}`.
5. Valid child targets move the card assignment to the selected child category's `Unclassified` leaf.
6. Valid `unclassified` targets keep the card assignment at the current scope's `Unclassified` leaf.
7. Invalid accepted results and terminal non-accepted outcomes record local processing state without moving assignments.
8. Lightweight polling/reconcile checks outstanding job links as a compensation path.

## Runtime Dependencies
- Redis is required for ingestion queue broker transport.
- Dramatiq is required for async worker execution.
- API and worker run in separate process containers from one shared app image.
- `job-queue-mcp` is required for taxonomy classification queue execution and result reads.
- OpenAI Embeddings API is required for worker ingestion and search query embedding.
- PostgreSQL remains persistent source of truth.
- Runtime configuration values are sourced from `.env` via `pydantic-settings`.

## Failure Handling
- Invalid request payloads are client-visible as `4xx`.
- Enqueue/worker/embedding/materialization failures for ingestion remain internal-only for endpoint behavior.
- Internal failures must be logged with correlation/debug-friendly fields.
- Taxonomy view endpoints do not return graph layout coordinates; frontend layout is client-owned.
- Taxonomy classification workers do not write knowledge APIs or databases.
- Taxonomy classification result processing moves assignments only after local validation against current taxonomy truth.

## Non-Goals (V1)
- Semantic-map snapshot/tile APIs.
- Keyword retrieval or hybrid retrieval.
- Ingestion processing-status exposure.
- Dead-letter queue policy matrix and queue durability optimization.
- HTTP-triggered taxonomy classification management APIs.

## Validation
- **Checks:**
  - `POST /api/v1/cards` contract checks (`4xx` invalid, `202` valid)
  - ingestion idempotency checks verifying first same-key submission publishes once and returns `202 Accepted`
  - ingestion idempotency checks verifying same-key same-payload replay returns `202 Accepted` without enqueueing duplicate ingestion work or materializing duplicate knowledge cards
  - ingestion idempotency checks verifying same-key conflicting payload returns `409 Conflict`
  - ingestion idempotency checks verifying timeout or connection-loss retry after an already accepted original request converges through same-key replay
  - ingestion worker checks verifying newly created nodes receive `Root -> Unclassified` assignment
  - `GET /api/v1/search` contract checks
  - `GET /api/v1/taxonomy/view/root`, `GET /api/v1/taxonomy/view/nodes/{id}`, and `POST /api/v1/taxonomy/view/leaves/{id}/details` contract checks
  - taxonomy classification queue-contract checks
  - taxonomy classification webhook/reconcile checks
  - taxonomy classification assignment-move checks
  - architecture checks that `search`/`ingestion` do not import `knowledge_graph.repo/model`
  - architecture checks that runtime API entrypoint does not import worker entrypoint
- **Evidence:**
  - passing API/worker integration tests and boundary checks
  - logs showing internal observability for async failure paths
