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
- **Scope/Boundaries:** Covers module ownership for frontend, backend API, business core, database, and reserved infrastructure modules.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Module Responsibilities

### Frontend
- **Responsibilities:**
  - Render a 2D knowledge-card network.
  - Provide viewport zoom and graph browsing interactions.
  - Render card layout and undirected edge visualization.
  - Provide V1 search interaction and query submission.
  - Consume read-only HTTP API responses for visualization.
- **Non-responsibilities:**
  - Filter interaction logic in V1.
  - Relation computation logic.
  - Domain truth ownership.
  - Backend persistence or infrastructure policy.

### Backend API
- **Responsibilities:**
  - Expose read-only HTTP API endpoints.
  - Expose V1 search read endpoints.
  - Validate request inputs and normalize response outputs.
  - Publish the API contract boundary for consumers.
- **Non-responsibilities:**
  - Domain relation computation strategy ownership.
  - Frontend rendering behavior ownership.
  - Storage-engine implementation ownership.

### Business Core
- **Responsibilities:**
  - Own read-use-case orchestration for cards and relations.
  - Define domain semantics for atomic cards and undirected relation strength.
  - Host offline cosine-similarity initialization logic for relation strength.
  - Provide domain read models to Backend API.
- **Non-responsibilities:**
  - HTTP transport concerns.
  - Frontend rendering concerns.
  - Infrastructure protocol details.

### Database
- **Responsibilities:**
  - Persist card and relation data as the system record source.
  - Serve read retrieval required by Business Core.
- **Non-responsibilities:**
  - API response shaping.
  - Frontend interaction behavior.
  - Business orchestration logic.

## Reserved Modules (Not Implemented in V1)

### Cache
- Reserved for future read acceleration.
- Not enabled in V1 runtime.

### Queue
- Reserved for future asynchronous workflows.
- Not enabled in V1 runtime.

### Object Storage
- Reserved for future large-object and asset storage.
- Not enabled in V1 runtime.

### External Services
- Reserved for future third-party capability integration.
- Not enabled in V1 runtime.

## Dependency Direction
- V1 runtime dependency direction is:
  - `Frontend -> Backend API -> Business Core -> Database`
- Reserved modules do not participate in V1 runtime behavior.

## V1 Boundary Summary
- V1 delivers read-only API serving, search, card-relation retrieval, and 2D graph browsing with zoom, layout, and edge rendering.
- V1 excludes filter interaction and excludes runtime dependency on cache, queue, object storage, and external services.
