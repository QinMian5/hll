---
abstract: Taxonomy module design for authoritative LCC tree truth, final node-to-leaf assignment, and drill-down view APIs.
out_of_scope: LLM classification orchestration internals, candidate ranking policy, and semantic-space snapshot architecture.
---

# Design: taxonomy

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy` module as the active browsing backbone: authoritative LCC tree storage, final leaf assignment truth, and taxonomy-query-driven view APIs.
- **Scope/Boundaries:** Covers taxonomy ownership, persistence shape, import boundaries, integrity constraints, and branch/leaf view contracts consumed by frontend React Flow pages.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth stays isolated by owner, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** LCC is a single authoritative tree stored in database; each knowledge node binds to exactly one taxonomy leaf; taxonomy browsing is query-driven from backend and not precomputed through semantic-map snapshot rebuilds.
- **Update Rule:** Requirement-level constraints remain stable while taxonomy structure and view API details are maintained here as implementation-facing truth.

## Design Approach
- **Approach:** Use taxonomy as the interaction truth for hierarchical drill-down browsing. Backend returns branch or leaf payloads from one taxonomy-view query surface. Frontend computes visual sizing and renders with React Flow.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy` owns taxonomy tree reads, final assignment reads/writes, taxonomy import orchestration, and taxonomy view API contracts.
  - **Authoritative source:** Persisted taxonomy tree is runtime/system truth. `human_workspace/LCC.yaml` is bootstrap input only.
  - **Tree stability model:** Taxonomy is one effectively stable tree. Active behavior excludes merge/update import and repeatable synchronization.
  - **Classification result model:** Each knowledge node binds to exactly one final taxonomy leaf.
  - **Assignment mutability rule:** First-write semantics for final assignment; no overwrite path.
  - **Browsing mode:** Drill-down click navigation (`root -> ... -> leaf`) replaces semantic-map zoom/tile browsing.
  - **Leaf graph scope rule:** Leaf view includes all inner cards for the leaf plus all one-hop outer neighbor cards; recursion depth is fixed to one hop.
  - **Edge scope rule:** Leaf view returns only `inner-inner` and `inner-outer` edges. `outer-outer` edges are excluded.
  - **Node scope marker:** Leaf graph node payload includes explicit `scope` field with values `inner` or `outer`.
  - **Leaf data-plane rule:** Leaf browsing is split into a skeleton graph surface and a node-detail surface. The skeleton surface carries the full one-hop graph topology needed for point-mode browsing. The detail surface carries `title` and `content` only for requested node ids.
  - **Leaf hydration rule:** Entering a leaf returns the full one-hop skeleton payload in one response and does not include node `title` or `content`.
  - **Leaf detail request rule:** Node details are fetched by explicit node-id batches scoped to the active leaf instead of being embedded in the initial leaf view payload.

## Persistence Projection

### taxonomy_nodes
- `id`: integer primary key.
- `parent_id`: nullable foreign key to `taxonomy_nodes.id`.
- `name`: non-null text.
- `depth`: non-null integer with `depth >= 0`.
- `is_leaf`: non-null boolean.
- Required constraints:
  - uniqueness over `(parent_id, name)`.
- Read-order rule:
  - sibling nodes are read with `ORDER BY name ASC`.

### node_taxonomy_assignments
- `id`: integer primary key.
- `node_id`: non-null foreign key to persisted knowledge node.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp.
- Required constraints:
  - uniqueness over `node_id`.
- Write-path rule:
  - assignment creation is insert-only and rejects writes when `node_id` already has an assignment.

### Trigger Rule
- Inserts and updates on `node_taxonomy_assignments` must be rejected unless `taxonomy_node_id` points to `taxonomy_nodes.is_leaf = true`.
- Trigger/function DDL is maintained by one dedicated migration scoped only to this trigger concern.

## Import Boundary
- Taxonomy bootstrap runs through a dedicated operator script.
- The import script reads `human_workspace/LCC.yaml`, computes `depth`, computes `is_leaf`, and inserts taxonomy rows.
- The import script fails immediately when taxonomy storage is non-empty.
- The import script does not merge or update existing taxonomy rows.
- Database initialization and migration flows do not auto-import taxonomy content.

## API Contract

### Root View Endpoint
- Route: `GET /taxonomy/view/root`
- Success payload:
  - no `current_node` field.
  - `breadcrumb` is an empty array.
  - `children` array for top-level taxonomy nodes (`parent_id is null`) with `descendant_card_count > 0`; each item:
    - `id`
    - `parent_id`
    - `name`
    - `depth`
    - `is_leaf`
    - `descendant_card_count`
- Failure behavior:
  - `404` when taxonomy store has no root node (for example, taxonomy not imported yet).

### Node View Endpoint
- Route: `GET /taxonomy/view/nodes/{node_id}`
- Success payload:
  - common envelope:
    - `node_kind`: `branch` or `leaf`
    - `current_node` object:
      - `id`
      - `parent_id`
      - `name`
      - `depth`
      - `is_leaf`
    - `breadcrumb` array ordered root-to-current, each item:
      - `id`
      - `parent_id`
      - `name`
      - `depth`
      - `is_leaf`
  - branch case (`node_kind=branch`):
    - `children` (direct children only) with `descendant_card_count > 0`, using the same child item shape as root endpoint
  - leaf case (`node_kind=leaf`):
    - `nodes` array, each item:
      - `id`
      - `scope` with value `inner` or `outer`
    - `edges` array, each item:
      - `id`
      - `source_node_id`
      - `target_node_id`
      - `strength`
- Failure behavior:
  - `404` when taxonomy node id is unknown.
  - `404` when taxonomy store is empty.
  - request-shape errors follow global error-governance behavior.

### Leaf Detail Endpoint
- Route: `POST /taxonomy/view/leaves/{node_id}/details`
- Request payload:
  - `node_ids`: non-empty array of unique positive integers
- Success payload:
  - `nodes` array ordered to match the request `node_ids`; each item:
    - `id`
    - `title`
    - `content`
- Failure behavior:
  - `404` when taxonomy leaf id is unknown.
  - `404` when the taxonomy store is empty.
  - `400` when `node_id` is not a leaf taxonomy node.
  - `400` when `node_ids` is empty, contains duplicates, or references a node outside the active leaf one-hop graph.

## Response Ordering Rules
- `breadcrumb` is ordered root-to-current.
- branch `children` are ordered by `name ASC`, tie-break by `id ASC`.
- leaf `nodes` are ordered by `id ASC`.
- leaf `edges` are deduplicated by undirected pair and ordered by `(source_node_id ASC, target_node_id ASC)`.
- every leaf `edges` item uses canonical undirected endpoint ordering with `source_node_id < target_node_id`.
- leaf detail `nodes` are ordered to match request `node_ids`.

## Read Responsibilities
- The taxonomy module provides:
  - complete taxonomy-tree reads and direct-child reads;
  - final assignment lookup for one knowledge node;
  - aggregate descendant counts for branch view payloads;
  - branch/leaf drill-down view payloads with breadcrumb context;
  - leaf node-detail hydration for explicit node-id batches within one active leaf graph.
- The taxonomy module does not provide:
  - candidate generation workflows;
  - confidence scoring workflows;
  - semantic-map snapshot/tile contracts.
  - authoritative node positions for frontend graph layout.

## Validation
- **Checks:**
  - Taxonomy import succeeds only when taxonomy store is empty.
  - Imported rows have correct `depth` and `is_leaf`.
  - Sibling reads return `ORDER BY name ASC`.
  - One knowledge node cannot have multiple assignments.
  - Non-leaf assignment writes are rejected by trigger.
  - `GET /taxonomy/view/root` returns top-level children list with `breadcrumb=[]`.
  - `GET /taxonomy/view/nodes/{id}` returns correct discriminated payload for branch/leaf.
  - Leaf skeleton payload excludes `outer-outer` edges and includes `scope` markers.
  - `POST /taxonomy/view/leaves/{id}/details` returns `title/content` only for requested node ids inside the active leaf graph.
- **Evidence:**
  - Passing import/repository/service tests and API contract tests for taxonomy view endpoints.
