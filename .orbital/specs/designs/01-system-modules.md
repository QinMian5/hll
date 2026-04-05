---
abstract: Module boundary and responsibility definition for the V1 API-first open knowledge network.
out_of_scope: Detailed implementation, framework-specific wiring, and storage-engine internals.
---

# Design: 01-system-modules

## Active Truth Policy
- This document defines only the currently accepted module boundaries.
- Superseded boundaries are removed instead of described as transition history.

## Context
- **Purpose:** Define module-level responsibilities, non-responsibilities, and dependency direction for V1.
- **Scope/Boundaries:** Covers module ownership for frontend, backend API, operator CLI, knowledge_graph, taxonomy, search, ingestion, semantic_map, offline/local auxiliary apps, database, and runtime infrastructure dependencies.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Module Responsibilities

### Frontend
- **Responsibilities:**
  - Render a 2D semantic map over a non-geospatial coordinate plane.
  - Provide viewport pan and semantic-zoom interactions.
  - Render region and label layers as the primary map expression.
  - Render atomic-card and local relation detail only at lower semantic levels.
  - Provide V1 search interaction and query submission.
  - Consume semantic-map and search read API responses for visualization and detail views.
- **Non-responsibilities:**
  - Filter interaction logic in V1.
  - Semantic-map projection, clustering, or snapshot computation.
  - Relation computation logic.
  - Domain truth ownership.
  - Backend persistence or infrastructure policy.

### Operator CLI
- **Responsibilities:**
  - Accept local `title` and `content` command parameters for a single card submission attempt.
  - Run a local agent review over only the current card input.
  - Emit machine-readable JSON review results and deterministic exit codes.
  - Call the ingestion accept API only after the local review passes.
- **Non-responsibilities:**
  - Graph persistence ownership.
  - Backend ingestion validation ownership.
  - Knowledge-base context retrieval for review decisions.
  - Cross-run memory or reviewer state retention.
  - Multi-card batch authoring workflows.

### Knowledge Corpus App
- **Responsibilities:**
  - Own local/offline source-document persistence for personal workflows.
  - Own isolated PostgreSQL full-text retrieval over source documents.
  - Own processed-document bookkeeping for excluding already handled source rows from later retrieval.
  - Expose importable Python-library services for record upsert, keyword search, and processed marking.
- **Contains:**
  - App-local settings, database session/metadata wiring, Alembic migrations, source-specific persistence models, repositories, and search/services for local source corpora.
- **Non-responsibilities:**
  - Online HTTP API exposure.
  - Operator-facing CLI command contracts in first version.
  - Knowledge-graph persistence ownership.
  - Existing CLI review orchestration.
  - Existing backend search or ingestion runtime behavior.
  - Import orchestration over filesystem paths or dump directories.

### Backend API
- **Responsibilities:**
  - Expose V1 search read endpoint.
  - Expose V1 semantic-map manifest and tile read endpoints.
  - Expose V1 ingestion accept endpoint.
  - Validate request inputs and normalize response outputs.
  - Publish the API contract boundary for consumers.
- **Non-responsibilities:**
  - Domain relation computation strategy ownership.
  - Semantic-map rebuild initiation through HTTP.
  - Frontend rendering behavior ownership.
  - Storage-engine implementation ownership.

### core Package
- **Responsibilities:**
  - Own foundational runtime contracts (`Settings`, global error primitives, logging setup).
  - Provide framework-agnostic foundation that can be imported by composition entrypoints.
- **Non-responsibilities:**
  - Dependency graph composition.
  - Domain orchestration and persistence query execution.
  - Module-to-module runtime wiring.

### entrypoints Package
- **Responsibilities:**
  - Own runtime composition and process entrypoints for API and worker.
  - Own singleton lifecycle assembly for engine/session/embedding client.
  - Own FastAPI dependency providers and Dramatiq actor registration.
- **Non-responsibilities:**
  - Domain business rule implementation.
  - Knowledge-graph persistence semantics ownership.

### knowledge_graph Module
- **Responsibilities:**
  - Own `Node/Edge/Adjacency` domain semantics and graph persistence truth.
  - Own repository and model access for graph persistence.
  - Provide read/write domain service ports consumed by `search`, `ingestion`, and `semantic_map`.
  - Execute node persistence and edge materialization in worker-triggered write flow.
- **Contains:**
  - Domain model projection, repository implementation, domain service, and domain DTO/port contracts.
- **Non-responsibilities:**
  - HTTP transport concerns.
  - Frontend rendering concerns.
  - Queue broker transport configuration.

### taxonomy Module
- **Responsibilities:**
  - Own the authoritative persisted LCC taxonomy tree.
  - Own final knowledge-node to taxonomy-leaf assignment truth.
  - Own taxonomy import orchestration from operator-supplied YAML input.
  - Provide read/write service ports consumed by downstream modules that need taxonomy structure or final assignments.
- **Contains:**
  - Taxonomy model projection, repository implementation, domain service, and taxonomy DTO/port contracts.
- **Non-responsibilities:**
  - Knowledge-node persistence ownership.
  - LLM classification orchestration and candidate workflow state.
  - Frontend rendering implementation.
  - Search query orchestration.
  - API entrypoint composition.

### search Module
- **Responsibilities:**
  - Own read-side search orchestration.
  - Build query embedding and request ranked retrieval through `knowledge_graph` read service port.
  - Shape read response with matched cards and connected titles.
- **Contains:**
  - Search API endpoint transport contract and read-side orchestration service logic.
- **Non-responsibilities:**
  - Direct repository or model access in `knowledge_graph`.
  - Semantic-map snapshot retrieval or publication.
  - Write-path orchestration.

### semantic_map Module
- **Responsibilities:**
  - Own semantic-map snapshot read contracts and read-side orchestration.
  - Own semantic-map snapshot rebuild orchestration for embedding projection, region geometry, label recommendation, and tile materialization.
  - Read taxonomy structure and final taxonomy assignments through `taxonomy` service ports when semantic-map rebuild requires top-level semantic structure truth.
  - Read graph-domain truth through `knowledge_graph` service ports when semantic-map rebuild requires knowledge-node and embedding source data.
  - Publish the current semantic-map snapshot used by frontend browsing.
  - Execute Phase 1 rebuild flow only when invoked by a dedicated operator command or script.
- **Contains:**
  - Semantic-map API transport contracts, snapshot read service logic, snapshot rebuild orchestration, and semantic-map DTO/port contracts.
- **Non-responsibilities:**
  - Direct repository or model access in `knowledge_graph`.
  - Search query orchestration.
  - Frontend rendering implementation.
  - Ingestion acceptance transport.
  - HTTP-triggered rebuild initiation.
  - Ingestion-coupled automatic snapshot rebuild enqueueing.

### ingestion Module
- **Responsibilities:**
  - Own write-side ingestion acceptance endpoint and async dispatch orchestration.
  - Own ingestion-scoped queue broker wiring and publish accepted jobs to Redis/Dramatiq worker execution.
  - Use project-managed Redis service on Docker backend network for queue transport.
  - Invoke `knowledge_graph` write service port for node persistence and edge materialization.
- **Contains:**
  - Ingestion API endpoint transport contract, ingestion queue broker setup, and worker job-processing primitives.
- **Non-responsibilities:**
  - Direct repository or model access in `knowledge_graph`.
  - Read-side search response orchestration.

## Runtime Infrastructure Dependencies (Enabled in V1)

### Queue
- Redis + Dramatiq are enabled to run ingestion asynchronous workflows.
- Redis is provided as a project-managed Docker service and consumed through backend-network service addressing (`redis://redis:6379/0`).

### External Services
- OpenAI Embeddings API integration is enabled for ingestion worker execution and search query embedding.
- The active embedding model is `text-embedding-3-small`.

## Reserved Modules (Not Implemented in V1)

### Cache
- Reserved for future read acceleration.
- Not enabled in V1 runtime.

### Object Storage
- Reserved for future large-object and asset storage.
- Not enabled in V1 runtime.

## Dependency Direction
- V1 runtime dependency direction is:
  - `Frontend -> Backend API(search) -> entrypoints.api -> search -> knowledge_graph -> Database`
  - `Frontend -> Backend API(semantic_map) -> entrypoints.api -> semantic_map -> taxonomy + knowledge_graph -> Database`
  - `Backend API(ingestion) -> entrypoints.api -> ingestion -> Redis/Dramatiq -> entrypoints.worker -> knowledge_graph -> Database`
  - `Operator CLI -> Backend API(ingestion) -> entrypoints.api -> ingestion -> Redis/Dramatiq -> entrypoints.worker -> knowledge_graph -> Database`
  - `Background taxonomy bootstrap execution -> taxonomy -> Database`
  - `Background semantic-map rebuild execution -> semantic_map -> taxonomy + knowledge_graph -> Database`
  - `core` is inbound-only (`entrypoints` and tooling import `core`; `core` does not import `entrypoints/modules/shared`).
- Local/offline auxiliary dependency direction is:
  - `External local scripts/programs -> Knowledge Corpus App -> Dedicated Knowledge Corpus PostgreSQL Service`
- Knowledge Corpus App does not participate in online V1 runtime behavior.
- Reserved modules do not participate in V1 runtime behavior.

## V1 Boundary Summary
- V1 delivers ingestion acceptance API, search read API, semantic-map read API, taxonomy-backed semantic structure truth, a local reviewed card-submission CLI, card-relation retrieval, and multi-scale semantic-map browsing.
- V1 excludes filter interaction and excludes runtime dependency on cache and object storage.
