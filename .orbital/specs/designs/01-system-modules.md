---
abstract: Module boundary and responsibility definition for the V1 public web, public MCP, private API, and project-owned source-processing pipeline.
out_of_scope: Detailed implementation, framework-specific wiring, and storage-engine internals.
---

# Design: 01-system-modules

## Active Truth Policy
- This document defines only currently accepted module boundaries.
- Superseded boundaries are removed instead of preserved as transition history.

## Context
- **Purpose:** Define module-level responsibilities, non-responsibilities, and dependency direction for V1.
- **Scope/Boundaries:** Covers ownership for browser frontend, web BFF, MCP service, backend API, operator CLI, knowledge_graph, taxonomy, taxonomy_classification, search, ingestion, source_pipeline, offline/local auxiliary apps, database, and runtime infrastructure dependencies.
- **Related Requirements:** R-001, R-003, R-004, R-005, R-006, R-007.

## Module Responsibilities

### Frontend
- **Responsibilities:**
  - Render taxonomy drill-down browsing with a branch-specific React Flow renderer and a leaf-specific deck.gl renderer inside one shared page shell.
  - Render branch view as direct child category bubbles.
  - Render leaf view as one-hop scoped relation graph (`inner` + pulled `outer` nodes).
  - Provide breadcrumb navigation for ancestor jumps.
  - Render the authenticated Dashboard token-management route for Logto personal access token lifecycle operations and MCP usage summaries.
  - Render authenticated Settings account profile surfaces from browser-safe BFF session/profile data.
  - Consume Search, Graph View, Dashboard, and Settings account profile data through browser-visible web API adapters owned by `apps/web`.
  - Render Search card edit affordances, authenticated suggestion submission UI, and anonymous sign-in-required UI through browser-visible web API adapters owned by `apps/web`.
  - Own graph layout calculation for branch and leaf views.
  - Render anonymous and logged-in session state exposed by the web BFF.
- **Non-responsibilities:**
  - Graph persistence ownership.
  - Relation computation logic.
  - Taxonomy assignment ownership.
  - Backend persistence, Logto session material, quota counters, or infrastructure policy.

### Web BFF
- **Responsibilities:**
  - Serve the public React web application.
  - Own browser-visible web data endpoints for Search, Graph View, and Dashboard token management.
  - Own browser-visible authenticated suggestion submission endpoints for Search card edit suggestions.
  - Own server-side Logto session handling for web users.
  - Own server-side Logto Account API profile reads and updates for authenticated web Settings surfaces.
  - Own server-side Logto Management API orchestration for signed-in users' personal access token lifecycle operations.
  - Own anonymous identity cookies and web quota enforcement.
  - Call the MCP service's internal usage-summary endpoint for dashboard token usage aggregates.
  - Call private backend APIs through generated contract artifacts over Docker-network HTTP.
- **Non-responsibilities:**
  - Backend domain logic.
  - Graph persistence ownership.
  - Taxonomy persistence ownership.
  - Public programmatic MCP access.
  - MCP usage persistence ownership.

### MCP Service
- **Responsibilities:**
  - Serve the public remote MCP endpoint.
  - Own MCP protocol handling, tool listing, and tool-call response shaping.
  - Expose the public `search` tool for external model clients.
  - Own Logto personal-access-token exchange and access-token validation for MCP callers.
  - Own MCP account-level quota, token-level quota, and usage attribution.
  - Own MCP usage-summary read semantics for internal dashboard consumption.
  - Call private backend search API through generated contract artifacts over Docker-network HTTP.
- **Non-responsibilities:**
  - Browser session ownership.
  - Public web route ownership.
  - Browser-facing Dashboard token lifecycle endpoint ownership.
  - Backend domain ranking semantics.
  - Graph persistence ownership.
  - Taxonomy persistence ownership.
  - Non-search MCP tools.

### Backend API
- **Responsibilities:**
  - Expose private V1 search read endpoint.
  - Expose private V1 card suggested-edit creation endpoint.
  - Expose private V1 taxonomy drill-down read endpoints.
  - Expose private V1 ingestion accept endpoint for accepted internal and operator workflows.
  - Validate request inputs and normalize response outputs.
  - Publish the authoritative OpenAPI contract boundary.
- **Non-responsibilities:**
  - Frontend rendering behavior ownership.
  - Browser session ownership.
  - Public web quota enforcement.
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
  - Own `Node/Edge/Adjacency`, card version, and card suggested-edit domain semantics and persistence truth.
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
  - Consume notification-only queue webhooks and low-frequency reconcile for queue results.
  - Hand off accepted review results to downstream consumers without storing them as durable business truth.
  - Own the following internal modules:
    - `pipeline_intake` for config ingestion and source-unit normalization
    - `pipeline_runtime` for notification-driven result consumption, low-frequency reconcile, and state transitions
    - `pipeline_webhook` for authenticated webhook intake and local event persistence
    - `page_to_card` for step input/output contracts
    - `card_review` for six-dimension review contracts
    - `card_repair` for repair step input/output contracts
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
- `job-queue-mcp-client` for Python producer/result-reader calls and machine-to-machine token acquisition against `job-queue-mcp`.
- Model Context Protocol Python SDK for the public MCP server.
- Logto personal access token exchange for public MCP caller authorization.
- Logto Account API for BFF-owned web account profile reads and updates.
- Logto Management API for BFF-owned web dashboard personal access token lifecycle operations.
- OpenAI Embeddings API for ingestion worker and search query embedding.
- PostgreSQL as persistent truth store for graph and taxonomy, plus dedicated app-local PostgreSQL services for `knowledge_corpus`, `source_pipeline`, and MCP usage records.

## Dependency Direction
- `Frontend -> Web BFF(search) -> Backend API(search) -> entrypoints.api -> search -> knowledge_graph -> Database`
- `MCP Client -> MCP Service(search) -> Backend API(search) -> entrypoints.api -> search -> knowledge_graph -> Database`
- `Frontend -> Web BFF(taxonomy view) -> Backend API(taxonomy view) -> entrypoints.api -> taxonomy -> knowledge_graph + taxonomy -> Database`
- `Frontend -> Web BFF(settings account profile) -> Logto Account API`
- `Frontend -> Web BFF(dashboard tokens) -> Logto Management API`
- `Web BFF(dashboard usage) -> MCP Service(internal usage summary) -> MCP usage database`
- `Backend API(ingestion) -> entrypoints.api -> ingestion -> Redis/Dramatiq -> entrypoints.worker -> knowledge_graph -> Database`
- `Operator CLI -> Backend API(ingestion) -> entrypoints.api -> ingestion -> Redis/Dramatiq -> entrypoints.worker -> knowledge_graph -> Database`
- `Background taxonomy bootstrap -> taxonomy -> Database`
- `Background taxonomy classification -> taxonomy_classification -> job-queue-mcp-client -> job-queue-mcp -> external workers`
- `Background taxonomy classification result application -> taxonomy_classification -> taxonomy + knowledge_graph -> Database`
- `External source adapter -> Source Pipeline App(pipeline_intake) -> Database`
- `Source Pipeline App(pipeline_runtime) -> job-queue-mcp-client -> job-queue-mcp -> external workers`
- `core` is inbound-only; it does not import `entrypoints/modules/shared`.

## V1 Boundary Summary
- V1 delivers ingestion acceptance API, search read API, public MCP search, web dashboard token management, taxonomy drill-down read APIs, taxonomy-backed structure truth, local reviewed card submission CLI, versioned knowledge-card history, authenticated suggested-edit submission, project-owned source-processing pipeline orchestration, and leaf-level one-hop relation browsing.
- V1 excludes semantic-map snapshot/tile browsing and excludes runtime cache/object-storage dependencies.
