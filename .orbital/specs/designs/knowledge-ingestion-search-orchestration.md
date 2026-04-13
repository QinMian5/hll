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
- Owns persisted LCC taxonomy tree and final node-to-leaf assignment truth.
- Owns taxonomy import orchestration from operator-supplied YAML.
- Owns taxonomy drill-down read orchestration:
  - `GET /taxonomy/view/root`
  - `GET /taxonomy/view/nodes/{node_id}`
  - `POST /taxonomy/view/leaves/{node_id}/details`
- Consumes `knowledge_graph` read ports for leaf-level one-hop graph payload shaping.

### taxonomy_classification
- Owns operator-triggered incremental classification orchestration for unassigned nodes.
- Runs one Cursor session per selected node.
- Consumes `knowledge_graph` and `taxonomy` service ports only.
- Persists final assignment through taxonomy first-write boundary.

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
- Route: `POST /cards`
- Request fields: `title`, `content`
- Response:
  - invalid payload: `4xx` via global error-governance mapping
  - valid payload: `202 Accepted`

### Search Endpoint
- Route: `GET /search?query=<string>`
- Response:
  - `matched_cards` with `title`, `content` only
  - `connected_titles`
- Limits:
  - `matched_cards <= 5`
  - `connected_titles <= 10`

### Taxonomy Root View Endpoint
- Route: `GET /taxonomy/view/root`
- Response:
  - no `current_node` field
  - `breadcrumb=[]`
  - `children[]` top-level taxonomy nodes (`parent_id is null`) filtered to `descendant_card_count > 0`
  - child item shape: `{id, parent_id, name, depth, is_leaf, descendant_card_count}`
  - children ordering: `name ASC`, tie-break `id ASC`
- Failure:
  - `404` when taxonomy has no root node.

### Taxonomy Node View Endpoint
- Route: `GET /taxonomy/view/nodes/{node_id}`
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
  - `404` when taxonomy store is empty.

### Taxonomy Leaf Detail Endpoint
- Route: `POST /taxonomy/view/leaves/{node_id}/details`
- Request:
  - `node_ids[]` non-empty array of unique positive integers scoped to the active leaf one-hop graph
- Response:
  - `nodes[]` ordered to match requested `node_ids`
  - node detail item shape: `{id, title, content}`
- Failure:
  - `404` when taxonomy leaf id is unknown
  - `404` when taxonomy store is empty
  - `400` when `node_id` is not a leaf taxonomy node
  - `400` when request `node_ids` is empty, contains duplicates, or references a node outside the active leaf one-hop graph

## Async Processing Flow
1. API validates ingestion request payload.
2. API returns `4xx` for invalid payload.
3. API publishes Dramatiq message through ingestion-owned publisher adapter.
4. API returns `202` for valid payload.
5. Worker actor receives task and requests embedding from OpenAI Embeddings API (`text-embedding-3-small`).
6. Worker persists node and edges through `knowledge_graph` write service.
7. Worker computes edge strength as `(dot_product + 1) / 2`, applies configured threshold/top-k, then persists `Edge` and `Adjacency`.

## Taxonomy Bootstrap Flow
1. Operator script reads `human_workspace/LCC.yaml`.
2. Script fails immediately when taxonomy storage already contains rows.
3. Script computes `depth` and `is_leaf`, then writes authoritative taxonomy tree.
4. Classification workflow later binds each knowledge node to one final taxonomy leaf.

## Taxonomy Classification Flow
1. Operator script selects unassigned nodes in deterministic order (`nodes.id ASC`).
2. Classifier runs one Cursor session per selected node.
3. Session traverses taxonomy progressively until a leaf is selected.
4. Session persists assignment via first-write `assign_leaf`.
5. Failed node attempts keep persistent truth unchanged.

## Runtime Dependencies
- Redis is required for ingestion queue broker transport.
- Dramatiq is required for async worker execution.
- API and worker run in separate process containers from one shared app image.
- OpenAI Embeddings API is required for worker ingestion and search query embedding.
- PostgreSQL remains persistent source of truth.
- Runtime configuration values are sourced from `.env` via `pydantic-settings`.

## Failure Handling
- Invalid request payloads are client-visible as `4xx`.
- Enqueue/worker/embedding/materialization failures for ingestion remain internal-only for endpoint behavior.
- Internal failures must be logged with correlation/debug-friendly fields.
- Taxonomy view endpoints do not return graph layout coordinates; frontend layout is client-owned.

## Non-Goals (V1)
- Semantic-map snapshot/tile APIs.
- Keyword retrieval or hybrid retrieval.
- Ingestion processing-status exposure.
- Dead-letter queue policy matrix and queue durability optimization.

## Validation
- **Checks:**
  - `POST /cards` contract checks (`4xx` invalid, `202` valid)
  - `GET /search` contract checks
  - `GET /taxonomy/view/root`, `GET /taxonomy/view/nodes/{id}`, and `POST /taxonomy/view/leaves/{id}/details` contract checks
  - architecture checks that `search`/`ingestion` do not import `knowledge_graph.repo/model`
  - architecture checks that runtime API entrypoint does not import worker entrypoint
- **Evidence:**
  - passing API/worker integration tests and boundary checks
  - logs showing internal observability for async failure paths
