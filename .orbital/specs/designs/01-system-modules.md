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
- **Scope/Boundaries:** Covers module ownership for frontend, backend API, knowledge, search, ingestion, database, and runtime infrastructure dependencies.
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

### knowledge Module
- **Responsibilities:**
  - Own `Node/Edge/Adjacency` domain semantics and graph persistence truth.
  - Own repository and model access for graph persistence.
  - Provide service-layer APIs consumed by `search` and `ingestion`.
  - Execute node persistence and edge materialization in worker-triggered write flow.
- **Non-responsibilities:**
  - HTTP transport concerns.
  - Frontend rendering concerns.
  - Queue broker protocol details.

### search Module
- **Responsibilities:**
  - Own read-side search orchestration.
  - Build query embedding and request cosine retrieval through `knowledge.service`.
  - Shape read response with matched cards and connected titles.
- **Non-responsibilities:**
  - Direct repository or model access in `knowledge`.
  - Write-path orchestration.

### ingestion Module
- **Responsibilities:**
  - Own write-side ingestion acceptance endpoint and async dispatch orchestration.
  - Publish accepted ingestion jobs to Redis/Dramatiq worker execution.
  - Invoke `knowledge.service` for node persistence and edge materialization.
- **Non-responsibilities:**
  - Direct repository or model access in `knowledge`.
  - Read-side search response orchestration.

## Runtime Infrastructure Dependencies (Enabled in V1)

### Queue
- Redis + Dramatiq are enabled to run ingestion asynchronous workflows.

### External Services
- Embedding service integration is enabled for ingestion worker execution and search query embedding.

## Reserved Modules (Not Implemented in V1)

### Cache
- Reserved for future read acceleration.
- Not enabled in V1 runtime.

### Object Storage
- Reserved for future large-object and asset storage.
- Not enabled in V1 runtime.

## Dependency Direction
- V1 runtime dependency direction is:
  - `Frontend -> Backend API(search) -> Search module -> Knowledge module -> Database`
  - `Backend API(ingestion) -> Ingestion module -> Redis/Dramatiq worker -> Knowledge module -> Database`
- Reserved modules do not participate in V1 runtime behavior.

## V1 Boundary Summary
- V1 delivers ingestion acceptance API, search read API, card-relation retrieval, and 2D graph browsing with zoom, layout, and edge rendering.
- V1 excludes filter interaction and excludes runtime dependency on cache and object storage.
