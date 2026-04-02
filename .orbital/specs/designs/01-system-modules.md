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
- **Scope/Boundaries:** Covers module ownership for frontend, backend API, knowledge_graph, search, ingestion, database, and runtime infrastructure dependencies.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Module Responsibilities

### Frontend
- **Responsibilities:**
  - Render a 2D knowledge-card network.
  - Provide viewport zoom and graph browsing interactions.
  - Render card layout and undirected edge visualization.
  - Provide V1 search interaction and query submission.
  - Consume search read API responses for visualization.
- **Non-responsibilities:**
  - Filter interaction logic in V1.
  - Relation computation logic.
  - Domain truth ownership.
  - Backend persistence or infrastructure policy.

### Backend API
- **Responsibilities:**
  - Expose V1 search read endpoint.
  - Expose V1 ingestion accept endpoint.
  - Validate request inputs and normalize response outputs.
  - Publish the API contract boundary for consumers.
- **Non-responsibilities:**
  - Domain relation computation strategy ownership.
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
  - Provide read/write domain service ports consumed by `search` and `ingestion`.
  - Execute node persistence and edge materialization in worker-triggered write flow.
- **Contains:**
  - Domain model projection, repository implementation, domain service, and domain DTO/port contracts.
- **Non-responsibilities:**
  - HTTP transport concerns.
  - Frontend rendering concerns.
  - Queue broker transport configuration.

### search Module
- **Responsibilities:**
  - Own read-side search orchestration.
  - Build query embedding and request cosine retrieval through `knowledge_graph` read service port.
  - Shape read response with matched cards and connected titles.
- **Contains:**
  - Search API endpoint transport contract and read-side orchestration service logic.
- **Non-responsibilities:**
  - Direct repository or model access in `knowledge_graph`.
  - Write-path orchestration.

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
  - `Backend API(ingestion) -> entrypoints.api -> ingestion -> Redis/Dramatiq -> entrypoints.worker -> knowledge_graph -> Database`
  - `core` is inbound-only (`entrypoints` and tooling import `core`; `core` does not import `entrypoints/modules/shared`).
- Reserved modules do not participate in V1 runtime behavior.

## V1 Boundary Summary
- V1 delivers ingestion acceptance API, search read API, card-relation retrieval, and 2D graph browsing with zoom, layout, and edge rendering.
- V1 excludes filter interaction and excludes runtime dependency on cache and object storage.
