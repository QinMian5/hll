---
abstract: Module-level orchestration design for knowledge core ownership, ingestion async write pipeline, and cosine-only search read flow.
out_of_scope: Keyword retrieval, hybrid reranking, ingestion status APIs, and distributed multi-region queue reliability.
---

# Design: knowledge-ingestion-search-orchestration

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted V1 module orchestration for `knowledge`, `ingestion`, and `search` under async ingestion with Redis and Dramatiq.
- **Scope/Boundaries:** Covers module ownership, endpoint contracts, asynchronous processing flow, data visibility rules, and runtime observability obligations.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, API contracts are authoritative and versioned, and behavior-changing details live in design documents.
- **Detail Commitments:** V1 runtime uses `FastAPI -> Redis -> Dramatiq worker -> PostgreSQL` for ingestion writes and cosine-only retrieval for search.
- **Update Rule:** Requirement-level constraints remain stable while this design captures all accepted runtime and contract details.

## Module Ownership

### knowledge
- Owns persistent domain truth for `Node`, `Edge`, and `Adjacency`.
- Is the only module allowed to own and access graph persistence models and repositories.
- Exposes service-layer APIs consumed by `search` and `ingestion`.
- Defines shared Pydantic DTOs used for cross-module validation.

### ingestion
- Owns write-side HTTP acceptance endpoint and write orchestration.
- Accepts valid payloads and returns `202 Accepted`.
- Publishes async jobs to Redis via Dramatiq.
- Uses project-managed Redis service on Docker backend network as queue broker target.
- Consumes embedding integration in worker execution path.
- Calls `knowledge.service` for node creation and edge materialization.
- Must not import `knowledge.repo` or `knowledge.model`.

### search
- Owns read-side HTTP search endpoint and read orchestration.
- Uses cosine-only query retrieval.
- Calls `knowledge.service` for candidate retrieval and connected-title expansion.
- Must not import `knowledge.repo` or `knowledge.model`.

## API Contract

### Ingestion Endpoint
- Route: `POST /ingestions/cards`
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
  - `connected_titles` returns at most `10` items.
  - `connected_titles` are deduplicated by `node_id` before projecting to titles.
  - `connected_titles` exclude titles already present in `matched_cards`.

## Async Processing Flow
1. API validates ingestion request payload.
2. API returns `4xx` for invalid payloads according to global error-governance mapping.
3. API publishes a Dramatiq message for valid payloads.
4. API returns `202` for valid payloads.
5. Worker receives message and requests embedding from OpenAI Embeddings API (`text-embedding-3-small`).
6. Worker calls `knowledge.service` to persist `Node`.
7. Worker computes cosine similarity and persists `Edge` and `Adjacency` rows.
8. Search path reads persisted graph data only; no processing-state data is exposed by search.

## Runtime Dependencies
- Redis is required as queue broker for ingestion.
- Queue runtime uses project-managed Redis Docker service (`redis`) and backend-network addressing (`redis://redis:6379/0`).
- Dramatiq is required for async worker execution.
- OpenAI Embeddings API is required in both ingestion worker flow and search query flow.
- Embedding model is fixed to `text-embedding-3-small` in MVP runtime defaults.
- PostgreSQL remains the persistent source of truth for graph entities.

## Failure Handling
- Invalid ingestion request payloads are client-visible as `4xx` according to global error-governance mapping.
- Enqueue, worker, embedding, and graph-materialization failures are internal-only for ingestion endpoint behavior.
- Internal failures must be recorded in structured logs with correlation identifiers.
- Search endpoint continues using unified visible error envelope for request/processing errors on the read path.

## Non-Goals (V1)
- Keyword retrieval or hybrid retrieval.
- Exposure of ingestion processing state to external clients.
- Dead-letter queue policy, retry policy matrix, and queue durability optimization.
- External callback/webhook for ingestion completion.

## Validation
- **Checks:**
  - Contract tests assert `POST /ingestions/cards` returns `4xx` on invalid payload and `202` on valid payload.
  - Search contract tests assert `matched_cards` include only `title` and `content`.
  - Architecture checks assert `search` and `ingestion` do not import `knowledge.repo/model`.
  - Integration tests verify worker-materialized nodes/edges become searchable.
- **Evidence:**
  - Passing test suite for API contracts, async worker flow, and architecture constraints.
  - Logs and metrics demonstrate internal observability for enqueue/worker failures.
