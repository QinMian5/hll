---
abstract: Module boundary and responsibility definition for the V1 API-first open knowledge network plus the project-owned source-processing pipeline.
out_of_scope: Detailed implementation, framework-specific wiring, and storage-engine internals.
---

# Design: 01-system-modules

## Active Truth Policy
- This document defines only currently accepted module boundaries.
- Superseded boundaries are removed instead of preserved as transition history.

## Context
- **Purpose:** Define module-level responsibilities, non-responsibilities, and dependency direction for V1.
- **Scope/Boundaries:** Covers ownership for frontend, backend API, operator CLI, knowledge_graph, taxonomy, taxonomy_classification, search, ingestion, source_pipeline, offline/local auxiliary apps, database, and runtime infrastructure dependencies.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Module Responsibilities

### Frontend
- **Responsibilities:**
  - Render taxonomy drill-down browsing with a branch-specific React Flow renderer and a leaf-specific deck.gl renderer inside one shared page shell.
  - Render branch view as direct child category bubbles.
  - Render leaf view as one-hop scoped relation graph (`inner` + pulled `outer` nodes).
  - Provide breadcrumb navigation for ancestor jumps.
  - Consume search and taxonomy view APIs through generated contracts.
  - Own graph layout calculation for branch and leaf views.
- **Non-responsibilities:**
  - Graph persistence ownership.
  - Relation computation logic.
  - Taxonomy assignment ownership.
  - Backend persistence or infrastructure policy.

### Backend API
- **Responsibilities:**
  - Expose V1 search read endpoint.
  - Expose V1 taxonomy drill-down read endpoints.
  - Expose V1 ingestion accept endpoint.
  - Validate request inputs and normalize response outputs.
  - Publish the authoritative OpenAPI contract boundary.
- **Non-responsibilities:**
  - Frontend rendering behavior ownership.
  - Semantic-map snapshot/tile APIs.
  - Storage-engine implementation ownership.

### core Package
- **Responsibilities:**
  - Own foundational runtime contracts (`Settings`, global errors, logging).
  - Provide framework-agnostic primitives imported by composition entrypoints.
- **Non-responsibilities:**
  - Dependency graph composition.
  - Domain orchestration and query execution.

### entrypoints Package
- **Responsibilities:**
  - Own runtime composition and process entrypoints for API and worker.
  - Own singleton lifecycle assembly for engine/session/embedding client.
  - Own FastAPI dependency providers and Dramatiq actor registration.
- **Non-responsibilities:**
  - Domain business-rule implementation.
  - Domain persistence semantics ownership.

### knowledge_graph Module
- **Responsibilities:**
  - Own `Node/Edge/Adjacency` domain semantics and persistence truth.
  - Own repository/model access for graph persistence.
  - Provide read/write service ports consumed by `search`, `ingestion`, and `taxonomy`.
  - Execute node persistence and edge materialization in worker write flow.
- **Non-responsibilities:**
  - HTTP transport concerns.
  - Frontend rendering concerns.
  - Queue broker transport ownership.

### taxonomy Module
- **Responsibilities:**
  - Own authoritative persisted operator-managed taxonomy tree.
  - Own the real single `Root` node and system-created `Unclassified` leaf buckets.
  - Own current knowledge-node to taxonomy-leaf assignment truth.
  - Own taxonomy import and operator structure mutation orchestration.
  - Own default assignment of newly created knowledge nodes to `Root -> Unclassified`.
  - Own assignment movement between valid taxonomy leaves.
  - Own taxonomy drill-down view read contracts:
    - `GET /api/v1/taxonomy/view/root`
    - `GET /api/v1/taxonomy/view/nodes/{node_id}`
    - `POST /api/v1/taxonomy/view/leaves/{node_id}/details`
  - Shape branch and leaf payloads (including breadcrumb and scope-marked leaf graph nodes).
- **Non-responsibilities:**
  - Knowledge-node persistence ownership.
  - LLM classification orchestration state.
  - Frontend rendering implementation.
  - Authoritative frontend node coordinate generation.
  - API entrypoint composition.

### taxonomy_classification Module
- **Responsibilities:**
  - Own operator-triggered job submission for cards in a scope node's `Unclassified` leaf.
  - Own job-queue-backed classification runtime state and result consumption.
  - Submit one `taxonomy_classification` queue job per selected card.
  - Consume notification-only webhooks and low-frequency reconcile for queue results.
  - Read accepted queue results through `job-queue-mcp` result surfaces.
  - Validate worker target decisions against taxonomy-owned current truth.
  - Move assignments through taxonomy-owned services.
  - Consume `knowledge_graph` and `taxonomy` service ports.
- **Non-responsibilities:**
  - Taxonomy persistence model ownership.
  - Knowledge-node persistence ownership.
  - Worker-side execution mechanics for queued jobs.
  - HTTP-triggered classification job APIs.

### search Module
- **Responsibilities:**
  - Own read-side search orchestration.
  - Build query embedding and request ranked retrieval through `knowledge_graph` read service port.
  - Shape read response with matched cards and connected titles.
- **Non-responsibilities:**
  - Direct repository/model access in `knowledge_graph`.
  - Write-path orchestration.

### ingestion Module
- **Responsibilities:**
  - Own write-side ingestion acceptance endpoint and async dispatch orchestration.
  - Own ingestion-scoped queue broker wiring and publish accepted jobs to Redis/Dramatiq worker flow.
  - Invoke `knowledge_graph` write service port for node persistence and edge materialization.
- **Non-responsibilities:**
  - Direct repository/model access in `knowledge_graph`.
  - Read-side search response orchestration.
  - Taxonomy classification ownership.

### Operator CLI
- **Responsibilities:**
  - Accept local `title` and `content` for single-card submission.
  - Run local agent review and emit deterministic JSON result.
  - Submit to ingestion API only after review passes.
- **Non-responsibilities:**
  - Backend persistence ownership.
  - Worker runtime ownership.
  - Batch multi-card authoring workflows.

### Knowledge Corpus App
- **Responsibilities:**
  - Own local/offline source-document persistence and keyword retrieval.
  - Own processed-document bookkeeping for local workflows.
  - Expose importable Python-library services for local corpus flows.
- **Non-responsibilities:**
  - Online API exposure.
  - Cross-app runtime ownership.
  - Main knowledge-graph persistence ownership.

### Source Pipeline App
- **Responsibilities:**
  - Own project-level source-processing intake, orchestration state, and long-running runtime for `job-queue-mcp` interactions.
  - Own app-local PostgreSQL persistence for source-pipeline orchestration state.
  - Materialize external source-processing configs into persisted `WorkflowRun` and `WorkflowUnit` state.
  - Persist only the local linkage state that `job-queue-mcp` cannot provide directly.
  - Fan out accepted `page-to-card` cards into per-card `card-review` jobs.
  - Hand off accepted review results to downstream consumers without storing them as durable business truth.
  - Own the following internal modules:
    - `pipeline_intake` for config ingestion and source-unit normalization
    - `pipeline_runtime` for polling and state transitions
    - `page_to_card` for step input/output contracts
    - `card_review` for six-dimension review contracts
    - `pipeline_handoff` for next-step or downstream delivery
- **Non-responsibilities:**
  - Source discovery or crawling policy.
  - Source-side processed bookkeeping.
  - Worker-side execution mechanics for queued jobs.
  - Online API exposure.
  - Final reviewed-card persistence ownership.

## Runtime Infrastructure Dependencies
- Redis + Dramatiq for ingestion asynchronous workflows.
- `job-queue-mcp` for `page-to-card`, `card-review`, `card-repair`, and `taxonomy_classification` job dispatch plus accepted-result retrieval.
- OpenAI Embeddings API for ingestion worker and search query embedding.
- PostgreSQL as persistent truth store for graph and taxonomy, plus dedicated app-local PostgreSQL services for `knowledge_corpus` and `source_pipeline`.

## Dependency Direction
- `Frontend -> Backend API(search) -> entrypoints.api -> search -> knowledge_graph -> Database`
- `Frontend -> Backend API(taxonomy view) -> entrypoints.api -> taxonomy -> knowledge_graph + taxonomy -> Database`
- `Backend API(ingestion) -> entrypoints.api -> ingestion -> Redis/Dramatiq -> entrypoints.worker -> knowledge_graph -> Database`
- `Operator CLI -> Backend API(ingestion) -> entrypoints.api -> ingestion -> Redis/Dramatiq -> entrypoints.worker -> knowledge_graph -> Database`
- `Background taxonomy bootstrap -> taxonomy -> Database`
- `Background taxonomy classification -> taxonomy_classification -> job-queue-mcp -> external workers`
- `Background taxonomy classification result application -> taxonomy_classification -> taxonomy + knowledge_graph -> Database`
- `External source adapter -> Source Pipeline App(pipeline_intake) -> Database`
- `Source Pipeline App(pipeline_runtime) -> job-queue-mcp -> external workers`
- `core` is inbound-only; it does not import `entrypoints/modules/shared`.

## V1 Boundary Summary
- V1 delivers ingestion acceptance API, search read API, taxonomy drill-down read APIs, taxonomy-backed structure truth, local reviewed card submission CLI, project-owned source-processing pipeline orchestration, and leaf-level one-hop relation browsing.
- V1 excludes semantic-map snapshot/tile browsing and excludes runtime cache/object-storage dependencies.
