---
abstract: Module-level orchestration design for knowledge core ownership, ingestion async write pipeline, cosine-only search read flow, and semantic-map snapshot source access.
out_of_scope: Keyword retrieval, hybrid reranking, ingestion status APIs, and distributed multi-region queue reliability.
---

# Design: knowledge-ingestion-search-orchestration

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted V1 module orchestration for `knowledge_graph`, `taxonomy`, `ingestion`, `search`, and semantic-map source access under async ingestion with Redis and Dramatiq.
- **Scope/Boundaries:** Covers module ownership, endpoint contracts, asynchronous processing flow, taxonomy bootstrap boundaries, semantic-map source-read rules, data visibility rules, and runtime observability obligations.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, API contracts are authoritative and versioned, and behavior-changing details live in design documents.
- **Detail Commitments:** V1 runtime uses `FastAPI -> Redis -> Dramatiq worker -> PostgreSQL` for ingestion writes and cosine-only retrieval for search.
- **Update Rule:** Requirement-level constraints remain stable while this design captures all accepted runtime and contract details.

## Module Ownership

### knowledge_graph
- Owns persistent domain truth for `Node`, `Edge`, and `Adjacency`.
- Is the only module allowed to own and access graph persistence models and repositories.
- Exposes read/write domain service ports consumed by `search`, `ingestion`, and `semantic_map`.
- Contains domain DTOs used by `knowledge_graph` service ports and repository outputs.
- Does not contain HTTP route handlers, queue broker configuration, or worker actor declarations.

### taxonomy
- Owns the persisted LCC taxonomy tree and the final knowledge-node to taxonomy-leaf assignment truth.
- Owns taxonomy import orchestration from operator-supplied YAML.
- Exposes read/write service ports consumed by `semantic_map` and later classification workflows.
- Does not own graph persistence truth, HTTP route handlers, or LLM candidate workflows.

### ingestion
- Owns write-side HTTP acceptance endpoint and write orchestration.
- Accepts valid payloads and returns `202 Accepted`.
- Owns ingestion-scoped queue broker configuration and message publishing adapter for async jobs to Redis via Dramatiq.
- Uses project-managed Redis service on Docker backend network as queue broker target.
- Consumes embedding integration in worker execution path.
- Calls `knowledge_graph` write service port for node creation and edge materialization.
- Contains `api.py`, `schema.py`, `service.py`, ingestion queue broker wiring, ingestion message-publisher adapter, and worker job-processing primitives.
- Must not import `knowledge_graph.repo` or `knowledge_graph.model`.
- Must not resolve runtime settings internally; ingestion runtime dependencies are injected from entrypoint composition providers.
- Must not import worker entrypoint modules under `entrypoints.worker`; API-side enqueue flow is module-owned and entrypoint-agnostic.

### search
- Owns read-side HTTP search endpoint and read orchestration.
- Uses cosine-only query retrieval.
- Calls `knowledge_graph` read service port for candidate retrieval and connected-title expansion.
- Contains `api.py`, `schema.py`, and read orchestration `service.py`.
- Does not contain queue broker setup, worker actor declarations, or write-path orchestration.
- Must not import `knowledge_graph.repo` or `knowledge_graph.model`.

### semantic_map
- Owns semantic-map snapshot read orchestration and snapshot rebuild orchestration.
- Calls `taxonomy` service ports for taxonomy structure and final assignment truth required by snapshot rebuilding and semantic-map reads.
- Calls `knowledge_graph` service ports for knowledge-node and embedding source truth required by snapshot rebuilding and semantic-map reads.
- Does not expose rebuild initiation as an HTTP API in Phase 1.
- Uses a dedicated operator command or script for rebuild initiation in Phase 1.
- Must not import `knowledge_graph.repo` or `knowledge_graph.model`.
- Must not import `taxonomy.repo` or `taxonomy.model`.

## API Contract

### Ingestion Endpoint
- Route: `POST /cards`
- Request body fields:
  - `title`
  - `content`
- Response contract:
  - Invalid request payload: `4xx` based on global error-governance mapping (`422` for request-shape invalidity, `400` for request-side use-case input invalidity).
  - Valid payload: `202 Accepted`.
  - Redis enqueue failures are internal-only and do not change the `202` contract.

### Search Endpoint
- Route: `GET /search?query=<string>`
- Request parameters:
  - `query`: required non-empty string.
- Success response:
  - `matched_cards`: list of objects containing only `title` and `content`.
  - `connected_titles`: list of titles.
- Response rules:
  - `matched_cards` returns at most `5` items.
  - `matched_cards` ordering is stable: cosine distance ascending, tie-break by `node_id` ascending.
  - `connected_titles` returns at most `10` items.
  - `connected_titles` are deduplicated by `node_id` before projecting to titles.
  - `connected_titles` exclude titles already present in `matched_cards`.
  - `connected_titles` ordering is stable: candidate traversal order is `matched_node_id` ascending, then `neighbor_node_id` ascending, then `neighbor_title` ascending; deduplication keeps the first occurrence per `neighbor_node_id`.

## Async Processing Flow
1. API validates ingestion request payload.
2. API returns `4xx` for invalid payloads according to global error-governance mapping.
3. API publishes a Dramatiq message through ingestion-owned publisher adapter for valid payloads.
4. API returns `202` for valid payloads.
5. Worker actor registry in `entrypoints/worker/actors.py` receives message and requests embedding from OpenAI Embeddings API (`text-embedding-3-small`).
6. Worker calls `knowledge_graph` write service port to persist `Node`.
7. Worker computes `dot_product`-mapped edge strength with `strength = (dot_product + 1) / 2`, keeps candidates with `strength >= 0.75`, selects at most the first `10`, and persists `Edge` and `Adjacency` rows.
8. Search path reads persisted graph data only; no processing-state data is exposed by search.

## Taxonomy Bootstrap Flow
1. An operator-run import script reads `human_workspace/LCC.yaml`.
2. The script fails immediately when taxonomy storage already contains rows.
3. The script computes `depth` and `is_leaf` for every taxonomy node and writes the authoritative taxonomy tree.
4. Later classification orchestration binds each knowledge node to one final taxonomy leaf through `taxonomy`.

## Runtime Dependencies
- Redis is required as queue broker for ingestion.
- Queue runtime uses project-managed Redis Docker service (`redis`) and backend-network addressing (`redis://redis:6379/0`).
- Dramatiq is required for async worker execution.
- API and worker run as separate process containers that share one application image and role-specific startup commands.
- OpenAI Embeddings API is required in both ingestion worker flow and search query flow.
- Embedding model is fixed to `text-embedding-3-small` in MVP runtime defaults.
- PostgreSQL remains the persistent source of truth for graph entities.
- Runtime configuration values are sourced from `.env` via `pydantic-settings`; YAML is not a runtime source.
- `load_settings()` usage is restricted to runtime composition entrypoints.
- `load_migration_settings()` usage is restricted to migration runtime entrypoints.

## Failure Handling
- Invalid ingestion request payloads are client-visible as `4xx` according to global error-governance mapping.
- Enqueue, worker, embedding, and graph-materialization failures are internal-only for ingestion endpoint behavior.
- Internal failures must be recorded in logs with correlation information (`request_id` where available) and debug-usable semantic fields.
- Search endpoint continues using unified visible error envelope for request/processing errors on the read path.

## Non-Goals (V1)
- Keyword retrieval or hybrid retrieval.
- Exposure of ingestion processing state to external clients.
- Dead-letter queue policy, retry policy matrix, and queue durability optimization.
- External callback/webhook for ingestion completion.

## Validation
- **Checks:**
  - Contract tests assert `POST /cards` returns `4xx` on invalid payload and `202` on valid payload.
  - Search contract tests assert `matched_cards` include only `title` and `content`.
  - Architecture checks assert `search` and `ingestion` do not import `knowledge_graph.repo/model`.
  - Architecture checks assert API entrypoint code does not import worker entrypoint modules.
  - Unit tests verify API enqueue composition depends on ingestion-owned publisher adapter instead of worker actor objects.
  - Integration tests verify worker-materialized nodes/edges become searchable.
- **Evidence:**
  - Passing test suite for API contracts, async worker flow, and architecture constraints.
  - Logs demonstrate internal observability for enqueue/worker failures.
