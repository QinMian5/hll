---
abstract: Taxonomy module design for authoritative operator-managed tree truth, backend-owned view read models, movable node-to-leaf assignments, canonical LCC route paths, and drill-down view APIs.
out_of_scope: AI classification job orchestration, worker-side execution mechanics, frontend visual styling, and semantic-space snapshot architecture.
---

# Design: taxonomy

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy` module as the active browsing backbone: authoritative operator-managed taxonomy tree storage, current node-to-leaf assignment truth, backend-owned taxonomy view read models, canonical LCC route paths, and taxonomy-query-driven view APIs.
- **Scope/Boundaries:** Covers taxonomy ownership, persistence shape, operator tree mutation boundaries, integrity constraints, assignment movement semantics, canonical route-path semantics, and branch/leaf view contracts consumed by the taxonomy browsing frontend.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth stays isolated by owner, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** Taxonomy is an operator-managed tree stored in the API database. The tree has one real `Root` node. Every regular taxonomy node has one system-created direct child leaf named `Unclassified`. Each knowledge node has exactly one current taxonomy leaf assignment. New knowledge nodes are assigned to `Root -> Unclassified` during ingestion. Taxonomy browsing is query-driven from backend-owned view read models and not precomputed through semantic-map snapshot rebuilds. Browser Graph View URLs use taxonomy-owned canonical LCC slug paths derived from the persisted taxonomy tree.
- **Update Rule:** Requirement-level constraints remain stable while taxonomy structure, mutation, assignment, and view API details are maintained here as implementation-facing truth.

## Design Approach
- **Approach:** Use taxonomy as the interaction truth for hierarchical drill-down browsing and incremental classification. Backend returns branch or leaf payloads from one taxonomy-view query surface. Operator scripts mutate taxonomy structure through taxonomy-owned services. Classification workers do not mutate taxonomy storage directly.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy` owns taxonomy tree reads, taxonomy tree writes, assignment reads/writes, default assignment resolution, and taxonomy view API contracts.
  - **Authoritative source:** Persisted taxonomy rows are runtime/system truth. Operator-provided classification outlines are inputs to taxonomy-owned import or mutation services.
  - **Root invariant:** Exactly one taxonomy node has `parent_id IS NULL`; its name is `Root`, its depth is `0`, and it is not a leaf.
  - **Unclassified bucket invariant:** Every regular taxonomy node has exactly one direct child named `Unclassified` with `is_leaf=true`. This child is a real taxonomy node in authoritative tree reads.
  - **System bucket naming rule:** The system-owned bucket name is exactly `Unclassified`. Parent names are not prefixed into bucket names.
  - **Assignment result model:** Each knowledge node binds to exactly one current taxonomy leaf.
  - **Assignment movement rule:** Assignment writes may create an initial leaf assignment or move an existing assignment to another valid taxonomy leaf.
  - **Default ingestion assignment rule:** New knowledge nodes are assigned to `Root -> Unclassified` after node creation succeeds.
  - **Classification movement rule:** When a card is classified into a direct child category of a scope node, its assignment moves to that child category's `Unclassified` leaf.
  - **Structure-node rule:** Regular category nodes are structure nodes. In this first version, cards are assigned to system `Unclassified` leaves; selecting a child category moves the card to that child's `Unclassified` leaf.
  - **Operator mutation rule:** First-version taxonomy structure mutation is script-driven. HTTP APIs do not expose taxonomy mutation commands.
  - **Child creation rule:** Creating a regular child category automatically creates its own `Unclassified` child leaf.
  - **Browsing mode:** Drill-down click navigation (`root -> ... -> leaf`) is the active browsing mode.
  - **Canonical route root rule:** The system `Root` node is represented by the browser route `/graph` and is excluded from descendant route paths.
  - **Canonical route slug rule:** Each taxonomy node has a route slug derived from its persisted display name by trimming whitespace, lowercasing, preserving ASCII letters and digits, replacing each contiguous run of non-alphanumeric characters with one hyphen, and trimming leading or trailing hyphens. For example, `Electronic computers. Computer science` becomes `electronic-computers-computer-science`, and `Science (General)` becomes `science-general`.
  - **Canonical route path rule:** A node's canonical route path is the slash-joined sequence of route slugs from the first child below `Root` through the node itself, excluding the system `Root` segment. For example, `Root -> Science -> Mathematics -> Algebra` maps to `science/mathematics/algebra`.
  - **Root route path rule:** The system `Root` node has `route_slug=root` and an empty `route_path` in response payloads.
  - **Sibling slug uniqueness rule:** Route slugs must be unique among siblings. Taxonomy import and operator structure mutation reject sibling sets whose persisted names produce the same route slug.
  - **Canonical path resolution rule:** Taxonomy path lookup resolves route paths segment-by-segment from the real `Root` node using sibling route slugs. Missing or ambiguous path segments fail rather than falling back to id lookup or name search.
  - **Branch visibility rule:** Branch payloads return direct children with `descendant_card_count > 0`. Direct children with no assigned cards anywhere in their descendant subtree are omitted from taxonomy view payloads.
  - **Leaf graph scope rule:** Leaf view includes all inner cards for the leaf plus all one-hop outer neighbor cards; recursion depth is fixed to one hop.
  - **Edge scope rule:** Leaf view returns only `inner-inner` and `inner-outer` edges. `outer-outer` edges are excluded.
  - **Node scope marker:** Leaf graph node payload includes explicit `scope` field with values `inner` or `outer`.
  - **Leaf layout ownership rule:** Leaf card graph layout is computed by the backend as stable global world coordinates through a deterministic static force simulation. Frontend clients use these world coordinates for viewport transforms and do not solve the leaf graph layout.
  - **Leaf layout force rule:** Leaf layout generation uses deterministic center-out spiral seeding, relation-strength link distance/strength, many-body repulsion, collision radius, and weak centering semantics aligned with the accepted legacy `d3-force` leaf graph behavior. The simulation runs to a fixed tick count and does not use runtime randomness.
  - **Leaf layout readable-scale rule:** Leaf layout generation uses the current `2x` readable graph scale for distance-bearing world geometry. Spiral seed radius, spiral radius step, relation link distances, relation-strength distance adjustment, and collision radius are scaled as world distances. The inverse-square many-body charge strength is scaled by the square of the readable graph scale so force displacement remains self-similar. Dimensionless link strength, collision strength, alpha decay, velocity retention, centering strength, and fixed tick count remain stable simulation controls.
  - **Leaf data-plane rule:** Leaf browsing is split into a leaf metadata surface, a viewport-scoped layout slice surface, a node-title surface, and a node-detail surface. The layout slice surface carries backend-computed world coordinates plus local topology for the requested world bounds. The node-title surface carries `title` only for requested node ids. The node-detail surface carries `title`, `content`, and `current_version` only for requested node ids.
  - **Leaf hydration rule:** Entering a leaf returns leaf metadata and does not include the full one-hop graph, node `title`, or node `content`.
  - **Leaf title request rule:** Node titles are fetched by explicit node-id batches scoped to the active leaf and are used for viewport-scoped point-title labels.
  - **Leaf detail request rule:** Node details are fetched by explicit node-id batches scoped to the active leaf; the initial leaf view payload excludes node `title`, `content`, and `current_version`.
  - **Leaf read-model rule:** Leaf browsing uses the authoritative current-assignment table for inner-node membership and one dedicated leaf projection table for one-hop edge membership. The projection stores only `(leaf_id, edge_id)` pairs and does not duplicate mutable edge fields such as `strength`.
  - **Read-performance rule:** Taxonomy view read paths must avoid full-graph or full-assignment work when the request scope is smaller. Root and branch payloads use cached descendant counts derived from current assignments. Leaf-specific reads must use leaf-scoped assignment lookups, leaf-scoped projection-edge reads, cached backend layout coordinates, viewport-bounded layout slice reads, and node-id-scoped detail reads.

## Persistence Projection

### taxonomy_nodes
- `id`: integer primary key.
- `parent_id`: nullable foreign key to `taxonomy_nodes.id`.
- `name`: non-null text.
- `depth`: non-null integer with `depth >= 0`.
- `is_leaf`: non-null boolean.
- `route_slug`: persisted non-empty text used for canonical browser paths.
- Required constraints:
  - uniqueness over `(parent_id, name)`.
  - uniqueness over `(parent_id, route_slug)`.
  - a partial unique index enforcing at most one row with `parent_id IS NULL`.
- Read-order rule:
  - sibling nodes are read with `ORDER BY name ASC`.
- Route-slug rule:
  - sibling nodes have unique route slugs under the same parent.
  - route slugs are derived from the display name used in the authoritative taxonomy tree.
  - persisted route slugs change only through taxonomy-owned structure import or mutation paths.
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

### Taxonomy View Redis Read Model
- Redis stores recomputable taxonomy view read models only. PostgreSQL remains the authoritative source for taxonomy nodes, current assignments, projection-edge membership, knowledge nodes, and edge fields. Mutation paths that change leaf assignment or projection-edge membership invalidate the affected leaf layout read model.
- Branch count read models store descendant card counts by taxonomy node id and support root and branch child filtering without scanning all assignments on every view request.
- Leaf layout read models store backend-computed global world coordinates for the one-hop leaf graph, layout bounds, layout algorithm version, generated timestamp, and node scope metadata.
- Redis cache keys include a schema or layout algorithm version so incompatible read-model shapes are not reused across implementation changes.
- Leaf layout cache keys include the active readable-scale layout algorithm version.
- Cache entries may be temporarily stale. Expired or missing entries are rebuilt from PostgreSQL truth.
- Rebuild paths use a Redis lock or equivalent single-flight guard so concurrent requests do not run duplicate expensive recomputations for the same read model.
- Redis loss, flush, or expiry must not create drift because every cached value is derived from PostgreSQL truth.

### Trigger Rule
- Inserts and updates on `node_taxonomy_assignments` must be rejected unless `taxonomy_node_id` points to `taxonomy_nodes.is_leaf = true`.
- Root uniqueness index DDL and leaf-only trigger/function DDL are maintained by API Alembic migrations scoped to taxonomy integrity concerns.

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

## Development Visualization Seed
- Local development may use a dedicated dev-only seed script to reset and recreate placeholder taxonomy branches, placeholder cards, hardcoded graph edges, card-to-leaf assignments, and taxonomy leaf projection rows for Graph View inspection.
- The development seed script does not call embedding providers and does not participate in production import, migration, ingestion, or classification flows.
- The development seed script must reject non-local database URLs before writing placeholder rows.

## API Contract

### Root View Endpoint
- Route: `GET /api/v1/taxonomy/view/root`
- Success payload:
  - no `current_node` field.
  - `breadcrumb` is an empty array.
  - `children` array for direct children of the real `Root` node whose descendant subtree contains at least one assigned card; each item:
    - `id`
    - `parent_id`
    - `name`
    - `route_slug`
    - `route_path`
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
      - `route_slug`
      - `route_path`
      - `depth`
      - `is_leaf`
    - `breadcrumb` array ordered root-to-current, each item:
      - `id`
      - `parent_id`
      - `name`
      - `route_slug`
      - `route_path`
      - `depth`
      - `is_leaf`
  - branch case (`node_kind=branch`):
    - `children` (direct children only, filtered to descendants with assigned cards) using the same child item shape as root endpoint
  - leaf case (`node_kind=leaf`):
    - `layout_version`
    - `world_bounds` object:
      - `min_x`
      - `min_y`
      - `max_x`
      - `max_y`
    - `node_count`
    - `edge_count`
    - `generated_at`
- Failure behavior:
  - `404` when taxonomy node id is unknown.
  - `404` when taxonomy root is unavailable.
  - request-shape errors follow global error-governance behavior.

### Path View Endpoint
- Route: `GET /api/v1/taxonomy/view/path/{route_path:path}`
- Request path:
  - `route_path` is a slash-joined canonical LCC slug path excluding the system `Root` segment.
  - the path parameter captures nested slash-separated segments.
- Success payload:
  - same response union as `GET /api/v1/taxonomy/view/nodes/{node_id}` for the resolved taxonomy node.
  - response nodes include `route_slug` and `route_path` so clients can navigate only through canonical paths returned by the taxonomy service.
- Failure behavior:
  - `404` when any path segment does not resolve below its current parent.
  - `404` when taxonomy root is unavailable.
  - request-shape errors follow global error-governance behavior.

### Leaf Layout Viewport Endpoint
- Route: `GET /api/v1/taxonomy/view/leaves/{node_id}/layout`
- Request query parameters:
  - `min_x`
  - `min_y`
  - `max_x`
  - `max_y`
- Success payload:
  - `leaf_id`
  - `layout_version`
  - `requested_bounds` object:
    - `min_x`
    - `min_y`
    - `max_x`
    - `max_y`
  - `nodes` array ordered by `id ASC`; each item:
    - `id`
    - `scope` with value `inner` or `outer`
    - `x`
    - `y`
  - `edges` array ordered by `(source_node_id ASC, target_node_id ASC)`; each item:
    - numeric tuple `[source_node_id, target_node_id, strength]`
- Slice rule:
  - the frontend sends world bounds that already include its desired viewport overscan.
  - `nodes` includes layout nodes whose world coordinate falls inside the requested bounds.
  - `edges` includes graph edges whose canonical source and target nodes are both present in the returned `nodes` set.
- Failure behavior:
  - `404` when taxonomy leaf id is unknown.
  - `404` when taxonomy root is unavailable.
  - `400` when `node_id` is not a leaf taxonomy node.
  - request-shape errors follow global error-governance behavior.

### Leaf Titles Endpoint
- Route: `POST /api/v1/taxonomy/view/leaves/{node_id}/titles`
- Request payload:
  - `node_ids`: non-empty array of unique positive integers
- Success payload:
  - `nodes` array ordered to match the request `node_ids`; each item:
    - `id`
    - `title`
- Failure behavior:
  - `404` when taxonomy leaf id is unknown.
  - `404` when taxonomy root is unavailable.
  - `400` when `node_id` is not a leaf taxonomy node.
  - `400` when `node_ids` is empty, contains duplicates, or references a node outside the active leaf one-hop graph.

### Leaf Detail Endpoint
- Route: `POST /api/v1/taxonomy/view/leaves/{node_id}/details`
- Request payload:
  - `node_ids`: non-empty array of unique positive integers
- Success payload:
  - `nodes` array ordered to match the request `node_ids`; each item:
    - `id`
    - `current_version`
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
- leaf layout slice `nodes` are ordered by `id ASC`.
- leaf layout slice `edges` are deduplicated by undirected pair and ordered by `(source_node_id ASC, target_node_id ASC)`.
- every leaf layout slice `edges` tuple uses canonical undirected endpoint ordering with `source_node_id < target_node_id`.
- leaf title `nodes` are ordered to match request `node_ids`.
- leaf detail `nodes` are ordered to match request `node_ids`.

## Read And Write Responsibilities
- The taxonomy module provides:
  - complete taxonomy-tree reads and direct-child reads;
  - root and `Unclassified` bucket lookup;
  - current assignment lookup for one knowledge node;
  - default assignment to `Root -> Unclassified`;
  - assignment movement between valid leaves;
  - regular child category creation with automatic `Unclassified` child creation;
  - cached aggregate descendant counts for branch view payloads;
  - branch/leaf drill-down view payloads with breadcrumb context;
  - backend-computed global world coordinates for leaf graph layout;
  - viewport-bounded leaf layout slices;
  - leaf node-title hydration for explicit node-id batches within one active leaf graph;
  - leaf node-detail hydration with current version for explicit node-id batches within one active leaf graph.
- The taxonomy module does not provide:
  - AI classification job submission or result consumption;
  - confidence scoring workflows;
  - semantic-map snapshot/tile contracts;
  - frontend camera state, pan/zoom transforms, hover state, selection state, or visual styling.

## Query Performance Projection
- Root and branch descendant counts are served from the Redis taxonomy view read model and recomputed from persisted current assignments on cache miss or expiry.
- The repository layer exposes a leaf-scoped assignment read that returns only the node ids assigned to one taxonomy leaf.
- Leaf graph edge expansion reads `edge_id` membership from `taxonomy_leaf_projection_edges` for the active `leaf_id`, then joins to `edges` to obtain current endpoints and `strength`.
- Leaf graph node scope is reconstructed from two sources only: inner membership from `node_taxonomy_assignments` and projected edge endpoints from `taxonomy_leaf_projection_edges`.
- Leaf layout generation computes stable global world coordinates from the leaf-scoped one-hop graph through the deterministic force simulation and stores the derived coordinates in Redis; leaf assignment and projection-edge writes invalidate affected cached layout coordinates before later reads reuse them.
- Leaf layout viewport reads return only nodes inside requested world bounds plus edges whose endpoints are both in the returned node set.
- Leaf title hydration validates requested node ids against cached leaf layout membership or leaf-scoped projection membership without loading content or current-version data for every node in that graph.
- Leaf title hydration reads `title` only for the requested node ids after membership validation succeeds.
- Leaf detail hydration validates requested node ids against cached leaf layout membership or leaf-scoped projection membership without loading title/content/current-version data for every node in that graph.
- Leaf detail hydration reads `title`, `content`, and `current_version` only for the requested node ids after membership validation succeeds.
- Taxonomy read performance behavior remains inside the taxonomy and knowledge-graph repository/service boundaries while the taxonomy view HTTP contracts expose backend-owned branch filtering and viewport-bounded leaf layout slices.

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
  - `GET /api/v1/taxonomy/view/root` returns non-empty direct children of `Root` with `breadcrumb=[]`.
  - `GET /api/v1/taxonomy/view/nodes/{id}` returns correct discriminated payload for branch/leaf.
  - Canonical route slug generation preserves ASCII letters and digits, lowercases names, collapses non-alphanumeric runs to single hyphens, and trims leading and trailing hyphens.
  - Taxonomy import and operator child creation reject sibling names that derive the same route slug.
  - `GET /api/v1/taxonomy/view/path/{route_path:path}` resolves nested canonical route paths to the same discriminated payload as the resolved node id.
  - `GET /api/v1/taxonomy/view/path/{route_path:path}` returns `404` when any path segment is missing below its current parent.
  - Branch node view payloads omit direct children whose descendant subtree has zero assigned cards.
  - Leaf node view payloads return metadata for backend layout consumption without returning the full one-hop graph.
  - `GET /api/v1/taxonomy/view/leaves/{id}/layout` returns backend-computed world coordinates and local edges for the requested world bounds.
  - Leaf layout generation responds to edge strength in the deterministic force geometry while remaining stable for identical inputs and layout algorithm version.
  - `POST /api/v1/taxonomy/view/leaves/{id}/titles` returns `title` only for requested node ids inside the active leaf graph.
  - `POST /api/v1/taxonomy/view/leaves/{id}/details` returns `title`, `content`, and `current_version` only for requested node ids inside the active leaf graph.
  - Leaf edge reads use the leaf projection table and stay scoped to the requested leaf graph.
  - Leaf detail hydration does not require loading title/content/current-version data for every node in the expanded one-hop graph.
  - Leaf-scoped assignment lookups use indexed access by `taxonomy_node_id`.
- **Evidence:**
  - Passing import/repository/service tests and API contract tests for taxonomy structure, assignment movement, and taxonomy view endpoints.
