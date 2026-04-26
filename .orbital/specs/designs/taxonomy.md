---
abstract: Taxonomy module design for authoritative operator-managed tree truth, visible Unclassified leaves, movable node-to-leaf assignments, and drill-down view APIs.
out_of_scope: AI classification job orchestration, worker-side execution mechanics, and semantic-space snapshot architecture.
---

# Design: taxonomy

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy` module as the active browsing backbone: authoritative operator-managed taxonomy tree storage, visible `Unclassified` bucket leaves, current node-to-leaf assignment truth, and taxonomy-query-driven view APIs.
- **Scope/Boundaries:** Covers taxonomy ownership, persistence shape, operator tree mutation boundaries, integrity constraints, assignment movement semantics, and branch/leaf view contracts consumed by the taxonomy browsing frontend.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth stays isolated by owner, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** Taxonomy is an operator-managed tree stored in the API database. The tree has one real `Root` node. Every regular taxonomy node has one system-created direct child leaf named `Unclassified`. Each knowledge node has exactly one current taxonomy leaf assignment. New knowledge nodes are assigned to `Root -> Unclassified` during ingestion. Taxonomy browsing is query-driven from backend and not precomputed through semantic-map snapshot rebuilds.
- **Update Rule:** Requirement-level constraints remain stable while taxonomy structure, mutation, assignment, and view API details are maintained here as implementation-facing truth.

## Design Approach
- **Approach:** Use taxonomy as the interaction truth for hierarchical drill-down browsing and incremental classification. Backend returns branch or leaf payloads from one taxonomy-view query surface. Operator scripts mutate taxonomy structure through taxonomy-owned services. Classification workers do not mutate taxonomy storage directly.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy` owns taxonomy tree reads, taxonomy tree writes, assignment reads/writes, default assignment resolution, and taxonomy view API contracts.
  - **Authoritative source:** Persisted taxonomy rows are runtime/system truth. Operator-provided classification outlines are inputs to taxonomy-owned import or mutation services.
  - **Root invariant:** Exactly one taxonomy node has `parent_id IS NULL`; its name is `Root`, its depth is `0`, and it is not a leaf.
  - **Unclassified bucket invariant:** Every regular taxonomy node has exactly one direct child named `Unclassified` with `is_leaf=true`. This child is a real taxonomy node and is visible through taxonomy view reads.
  - **System bucket naming rule:** The system-owned bucket name is exactly `Unclassified`. Parent names are not prefixed into bucket names.
  - **Assignment result model:** Each knowledge node binds to exactly one current taxonomy leaf.
  - **Assignment movement rule:** Assignment writes may create an initial leaf assignment or move an existing assignment to another valid taxonomy leaf.
  - **Default ingestion assignment rule:** New knowledge nodes are assigned to `Root -> Unclassified` after node creation succeeds.
  - **Classification movement rule:** When a card is classified into a direct child category of a scope node, its assignment moves to that child category's `Unclassified` leaf.
  - **Structure-node rule:** Regular category nodes are structure nodes. In this first version, cards are assigned to system `Unclassified` leaves; selecting a child category moves the card to that child's `Unclassified` leaf.
  - **Operator mutation rule:** First-version taxonomy structure mutation is script-driven. HTTP APIs do not expose taxonomy mutation commands.
  - **Child creation rule:** Creating a regular child category automatically creates its own `Unclassified` child leaf.
  - **Browsing mode:** Drill-down click navigation (`root -> ... -> leaf`) is the active browsing mode.
  - **Branch visibility rule:** Branch payloads return direct children with `descendant_card_count`; empty operator-created categories and `Unclassified` bucket leaves remain representable in the tree response.
  - **Leaf graph scope rule:** Leaf view includes all inner cards for the leaf plus all one-hop outer neighbor cards; recursion depth is fixed to one hop.
  - **Edge scope rule:** Leaf view returns only `inner-inner` and `inner-outer` edges. `outer-outer` edges are excluded.
  - **Node scope marker:** Leaf graph node payload includes explicit `scope` field with values `inner` or `outer`.
  - **Leaf data-plane rule:** Leaf browsing is split into a skeleton graph surface and a node-detail surface. The skeleton surface carries the full one-hop graph topology needed for point-mode browsing. The detail surface carries `title` and `content` only for requested node ids.
  - **Leaf hydration rule:** Entering a leaf returns the full one-hop skeleton payload in one response and does not include node `title` or `content`.
  - **Leaf detail request rule:** Node details are fetched by explicit node-id batches scoped to the active leaf; the initial leaf view payload excludes node `title` and `content`.
  - **Leaf read-model rule:** Leaf browsing uses the authoritative current-assignment table for inner-node membership and one dedicated leaf projection table for one-hop edge membership. The projection stores only `(leaf_id, edge_id)` pairs and does not duplicate mutable edge fields such as `strength`.
  - **Read-performance rule:** Taxonomy view read paths must avoid full-graph or full-assignment work when the request scope is smaller. Root and branch payloads may aggregate descendant counts across the tree, but leaf-specific reads must use leaf-scoped assignment lookups, leaf-scoped projection-edge reads, and node-id-scoped detail reads.

## Persistence Projection

### taxonomy_nodes
- `id`: integer primary key.
- `parent_id`: nullable foreign key to `taxonomy_nodes.id`.
- `name`: non-null text.
- `depth`: non-null integer with `depth >= 0`.
- `is_leaf`: non-null boolean.
- Required constraints:
  - uniqueness over `(parent_id, name)`.
  - a partial unique index enforcing at most one row with `parent_id IS NULL`.
- Read-order rule:
  - sibling nodes are read with `ORDER BY name ASC`.
- Root rule:
  - exactly one persisted node is the root node; storage enforces at most one root row and taxonomy bootstrap/service code ensures the row exists.
- Unclassified rule:
  - each regular taxonomy node has a direct child named `Unclassified`.
  - `Unclassified` children are leaves.

### node_taxonomy_assignments
- `id`: integer primary key.
- `node_id`: non-null foreign key to persisted knowledge node.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp recording the current assignment write.
- Required constraints:
  - uniqueness over `node_id`.
- Required access paths:
  - indexed lookup by `taxonomy_node_id`.
  - indexed lookup by `(taxonomy_node_id, node_id)` for leaf-scoped node membership reads.
- Write-path rule:
  - assignment writes are upserts by `node_id`.
  - moving a node updates the existing row's `taxonomy_node_id` and current assignment timestamp.

### taxonomy_leaf_projection_edges
- `leaf_id`: non-null foreign key to `taxonomy_nodes.id`.
- `edge_id`: non-null foreign key to `edges.id`.
- Required constraints:
  - primary key over `(leaf_id, edge_id)`.
- Required access paths:
  - indexed read by `leaf_id`.
  - indexed reverse lookup by `edge_id` for incremental maintenance when an edge changes.
- Read-model rule:
  - one row means the referenced edge belongs to the one-hop projection for the referenced leaf.
  - the table stores only leaf-edge membership and does not duplicate `node_a_id`, `node_b_id`, or `strength`.
- Derivation rule:
  - inner nodes come from `node_taxonomy_assignments`.
  - outer nodes are derived at read time from the endpoints of the projected edges after subtracting the inner node set.
- Incremental-maintenance rule:
  - assigning or moving a node refreshes projection rows for affected source and target leaves.
  - creating an edge inserts projection rows for the leaf of each endpoint node, resulting in one row when both endpoints share a leaf and at most two rows otherwise.
  - mutable edge fields such as `strength` are read from `edges` at query time through `edge_id` and are not copied into the projection.

### Trigger Rule
- Inserts and updates on `node_taxonomy_assignments` must be rejected unless `taxonomy_node_id` points to `taxonomy_nodes.is_leaf = true`.
- Root uniqueness index DDL and leaf-only trigger/function DDL are maintained by dedicated migrations scoped to taxonomy integrity concerns.

## Operator Structure Mutation Boundary
- Taxonomy structure mutation runs through dedicated operator scripts backed by taxonomy-owned services.
- The root creation/import path creates one `Root` node and `Root -> Unclassified`.
- Operator scripts may create one or more regular direct children under an existing scope node.
- Creating a regular child category also creates that child category's direct `Unclassified` leaf.
- Operator scripts reject duplicate sibling names under the same parent.
- Operator scripts reject direct human creation of duplicate `Unclassified` children.
- Database initialization and migration flows do not auto-import operator taxonomy content.

## Operator Assignment Backfill
- Knowledge nodes without a taxonomy assignment are assigned through a dedicated operator backfill command.
- The command defaults to a read-only dry run and requires an explicit confirmation flag before writing assignments.
- The command ensures `Root` and `Root -> Unclassified` through taxonomy-owned services before applying assignment writes.
- The command inserts assignments only for knowledge nodes that do not already have a `node_taxonomy_assignments` row.
- Existing assignments are never moved by the backfill command.
- Apply mode rebuilds taxonomy leaf projection rows after assignment writes so taxonomy leaf views read current one-hop edge membership.

## API Contract

### Root View Endpoint
- Route: `GET /api/v1/taxonomy/view/root`
- Success payload:
  - no `current_node` field.
  - `breadcrumb` is an empty array.
  - `children` array for direct children of the real `Root` node; each item:
    - `id`
    - `parent_id`
    - `name`
    - `depth`
    - `is_leaf`
    - `descendant_card_count`
- Failure behavior:
  - `404` when the real `Root` node is unavailable.

### Node View Endpoint
- Route: `GET /api/v1/taxonomy/view/nodes/{node_id}`
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
    - `children` (direct children only) using the same child item shape as root endpoint
  - leaf case (`node_kind=leaf`):
    - `nodes` array, each item:
      - `id`
      - `scope` with value `inner` or `outer`
    - `edges` array, each item:
      - numeric tuple `[source_node_id, target_node_id, strength]`
- Failure behavior:
  - `404` when taxonomy node id is unknown.
  - `404` when taxonomy root is unavailable.
  - request-shape errors follow global error-governance behavior.

### Leaf Detail Endpoint
- Route: `POST /api/v1/taxonomy/view/leaves/{node_id}/details`
- Request payload:
  - `node_ids`: non-empty array of unique positive integers
- Success payload:
  - `nodes` array ordered to match the request `node_ids`; each item:
    - `id`
    - `title`
    - `content`
- Failure behavior:
  - `404` when taxonomy leaf id is unknown.
  - `404` when taxonomy root is unavailable.
  - `400` when `node_id` is not a leaf taxonomy node.
  - `400` when `node_ids` is empty, contains duplicates, or references a node outside the active leaf one-hop graph.

## Response Ordering Rules
- `breadcrumb` is ordered root-to-current.
- branch `children` are ordered by `name ASC`, tie-break by `id ASC`.
- leaf `nodes` are ordered by `id ASC`.
- leaf `edges` are deduplicated by undirected pair and ordered by `(source_node_id ASC, target_node_id ASC)`.
- every leaf `edges` tuple uses canonical undirected endpoint ordering with `source_node_id < target_node_id`.
- leaf detail `nodes` are ordered to match request `node_ids`.

## Read And Write Responsibilities
- The taxonomy module provides:
  - complete taxonomy-tree reads and direct-child reads;
  - root and `Unclassified` bucket lookup;
  - current assignment lookup for one knowledge node;
  - default assignment to `Root -> Unclassified`;
  - assignment movement between valid leaves;
  - regular child category creation with automatic `Unclassified` child creation;
  - aggregate descendant counts for branch view payloads;
  - branch/leaf drill-down view payloads with breadcrumb context;
  - leaf node-detail hydration for explicit node-id batches within one active leaf graph.
- The taxonomy module does not provide:
  - AI classification job submission or result consumption;
  - confidence scoring workflows;
  - semantic-map snapshot/tile contracts;
  - authoritative node positions for frontend graph layout.

## Query Performance Projection
- Root and branch descendant counts are computed from persisted current assignments, but leaf-specific read paths do not load the full assignment table when one leaf id is already known.
- The repository layer exposes a leaf-scoped assignment read that returns only the node ids assigned to one taxonomy leaf.
- Leaf graph edge expansion reads `edge_id` membership from `taxonomy_leaf_projection_edges` for the active `leaf_id`, then joins to `edges` to obtain current endpoints and `strength`.
- Leaf graph node scope is reconstructed from two sources only: inner membership from `node_taxonomy_assignments` and projected edge endpoints from `taxonomy_leaf_projection_edges`.
- Leaf detail hydration validates requested node ids against the active one-hop graph without loading title/content for every node in that graph.
- Leaf detail hydration reads `title` and `content` only for the requested node ids after membership validation succeeds.
- Taxonomy read performance fixes remain inside the taxonomy and knowledge-graph repository/service boundaries and do not change the external HTTP contracts.

## Validation
- **Checks:**
  - Taxonomy bootstrap creates exactly one `Root` node and `Root -> Unclassified`.
  - Storage rejects a second `taxonomy_nodes` row with `parent_id IS NULL`.
  - Taxonomy bootstrap creates the persisted root row with `name='Root'`, `depth=0`, and `is_leaf=false`.
  - Regular child creation creates the requested category nodes and each child's `Unclassified` leaf.
  - Sibling reads return `ORDER BY name ASC`.
  - One knowledge node has exactly one current assignment row.
  - Assignment moves update the current leaf without creating duplicate rows.
  - New ingestion-created nodes receive assignment to `Root -> Unclassified`.
  - Operator backfill assigns only unassigned knowledge nodes to `Root -> Unclassified`.
  - Non-leaf assignment writes are rejected by trigger.
  - `GET /api/v1/taxonomy/view/root` returns direct children of `Root` with `breadcrumb=[]`.
  - `GET /api/v1/taxonomy/view/nodes/{id}` returns correct discriminated payload for branch/leaf.
  - Leaf skeleton payload excludes `outer-outer` edges and includes `scope` markers.
  - `POST /api/v1/taxonomy/view/leaves/{id}/details` returns `title/content` only for requested node ids inside the active leaf graph.
  - Leaf edge reads use the leaf projection table and stay scoped to the requested leaf graph.
  - Leaf detail hydration does not require loading title/content for every node in the expanded one-hop graph.
  - Leaf-scoped assignment lookups use indexed access by `taxonomy_node_id`.
- **Evidence:**
  - Passing import/repository/service tests and API contract tests for taxonomy structure, assignment movement, and taxonomy view endpoints.
