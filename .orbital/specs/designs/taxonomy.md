---
abstract: Taxonomy module design for authoritative operator-managed LCC tree truth, backend-owned Redis view read models, direct node-to-taxonomy assignments, canonical LCC route paths, virtual Unclassified view scopes, and drill-down view APIs.
out_of_scope: AI classification job orchestration, worker-side execution mechanics, frontend visual styling, and semantic-space snapshot architecture.
---

# Design: taxonomy

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy` module as the active browsing backbone: authoritative operator-managed LCC taxonomy tree storage, current direct node-to-taxonomy assignment truth, backend-owned Redis taxonomy view read models, canonical LCC route paths, virtual Unclassified view scopes, and taxonomy-query-driven view APIs.
- **Scope/Boundaries:** Covers taxonomy ownership, persistence shape, operator tree mutation boundaries, integrity constraints, assignment movement semantics, canonical route-path semantics, and branch/card-scope view contracts consumed by the taxonomy browsing frontend.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth stays isolated by owner, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** Taxonomy is an operator-managed LCC tree stored in the API database. The tree has one real `Root` node. Persisted taxonomy rows represent real LCC categories only. Each knowledge node has exactly one current assignment to a real taxonomy node. New knowledge nodes are assigned directly to `Root` during ingestion. Taxonomy browsing is query-driven from backend-owned view read models and not precomputed through semantic-map snapshot rebuilds. Browser Graph View URLs use taxonomy-owned canonical LCC slug paths derived from the persisted taxonomy tree, with path-addressed virtual Unclassified scopes assembled by the service layer when a node has both directly assigned cards and visible child categories.
- **Update Rule:** Requirement-level constraints remain stable while taxonomy structure, mutation, assignment, and view API details are maintained here as implementation-facing truth.

## Design Approach
- **Approach:** Use taxonomy as the interaction truth for hierarchical drill-down browsing and incremental classification. Backend returns branch or leaf payloads from one taxonomy-view query surface. Operator scripts mutate taxonomy structure through taxonomy-owned services. Classification workers do not mutate taxonomy storage directly.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy` owns taxonomy tree reads, taxonomy tree writes, assignment reads/writes, default assignment resolution, and taxonomy view API contracts.
  - **Authoritative source:** Persisted taxonomy rows are runtime/system truth. Operator-provided classification outlines are inputs to taxonomy-owned import or mutation services.
  - **Root invariant:** Exactly one taxonomy node has `parent_id IS NULL`; its name is `Root`, its depth is `0`, and it is not a leaf.
  - **Persisted category invariant:** Persisted taxonomy rows represent real LCC categories. Service-owned view buckets are assembled in response payloads and are not persisted as taxonomy rows.
  - **Assignment result model:** Each knowledge node binds to exactly one current real taxonomy node.
  - **Assignment movement rule:** Assignment writes may create an initial assignment or move an existing assignment to another real taxonomy node.
  - **Default ingestion assignment rule:** New knowledge nodes are assigned directly to `Root` after node creation succeeds.
  - **Classification movement rule:** When a card is classified into a direct child category of a scope node, its assignment moves directly to that child category.
  - **Dynamic node-kind rule:** A taxonomy node's branch or card-scope behavior is derived from current structure and direct assignments. A node with visible child categories is a branch. A node with directly assigned cards and no visible child categories is a real card scope. A node with both directly assigned cards and visible child categories exposes those directly assigned cards through a virtual `Unclassified` child scope.
  - **Virtual Unclassified identity rule:** A virtual `Unclassified` scope is identified by its canonical path below the parent taxonomy node, not by a taxonomy node id. The virtual scope uses the fixed route segment `unclassified` below the parent route path.
  - **Operator mutation rule:** Taxonomy structure mutation is script-driven. HTTP APIs do not expose taxonomy mutation commands.
  - **Child creation rule:** Creating a child category creates only the requested real LCC taxonomy node.
  - **Browsing mode:** Drill-down click navigation (`root -> ... -> leaf`) is the active browsing mode.
  - **Canonical route root rule:** The system `Root` node is represented by the browser route `/graph` and is excluded from descendant route paths.
  - **Canonical route slug rule:** Each taxonomy node has a route slug derived from its persisted display name by trimming whitespace, lowercasing, preserving ASCII letters and digits, replacing each contiguous run of non-alphanumeric characters with one hyphen, and trimming leading or trailing hyphens. For example, `Electronic computers. Computer science` becomes `electronic-computers-computer-science`, and `Science (General)` becomes `science-general`.
  - **Canonical route path rule:** A node's canonical route path is the slash-joined sequence of route slugs from the first child below `Root` through the node itself, excluding the system `Root` segment. For example, `Root -> Science -> Mathematics -> Algebra` maps to `science/mathematics/algebra`.
  - **Root route path rule:** The system `Root` node has `route_slug=root` and an empty `route_path` in response payloads.
  - **Sibling slug uniqueness rule:** Route slugs must be unique among siblings. Taxonomy import and operator structure mutation reject sibling sets whose persisted names produce the same route slug.
  - **Canonical path resolution rule:** Taxonomy path lookup resolves route paths segment-by-segment from the real `Root` node using sibling route slugs. Missing or ambiguous path segments fail rather than falling back to id lookup or name search.
  - **Branch visibility rule:** Branch payloads return direct children with `descendant_card_count > 0`. Direct children with no assigned cards anywhere in their descendant subtree are omitted from taxonomy view payloads.
  - **Card-scope graph rule:** Card-scope view includes all directly assigned inner cards for the active taxonomy or virtual scope plus all one-hop outer neighbor cards; recursion depth is fixed to one hop.
  - **Edge scope rule:** Card-scope view returns only `inner-inner` and `inner-outer` edges. `outer-outer` edges are excluded.
  - **Node scope marker:** Card graph node payload includes explicit `scope` field with values `inner` or `outer`.
  - **Layout ownership rule:** Card-scope graph layout is computed by the backend as stable global world coordinates through a deterministic static force simulation. Frontend clients use these world coordinates for viewport transforms and do not solve the graph layout.
  - **Layout force rule:** Layout generation uses deterministic center-out spiral seeding, relation-strength link distance/strength, many-body repulsion, collision radius, and weak centering semantics aligned with the current `d3-force` graph behavior. The simulation runs to a fixed tick count and does not use runtime randomness.
  - **Layout readable-scale rule:** Layout generation uses the current `2x` readable graph scale for distance-bearing world geometry. Spiral seed radius, spiral radius step, relation link distances, relation-strength distance adjustment, and collision radius are scaled as world distances. The inverse-square many-body charge strength is scaled by the square of the readable graph scale so force displacement remains self-similar. Dimensionless link strength, collision strength, alpha decay, velocity retention, centering strength, and fixed tick count remain stable simulation controls.
  - **Layout readiness rule:** Card-scope metadata and viewport layout responses require a valid full layout Redis read model for the requested scope identity and active layout version. If the read model is missing or expired, the API registers one Redis-backed compute request for that scope/version and returns `503 layout_not_ready` with `Retry-After`.
  - **Layout single-flight rule:** Redis pending and running state is keyed by card-scope identity and active layout version. Concurrent requests for the same scope/version do not enqueue or execute duplicate layout computations; they return `layout_not_ready` while one compute request is pending or running.
  - **Layout compute role rule:** CPU-bound card-scope layout computation runs only in the dedicated taxonomy view layout runtime. API request handlers resolve taxonomy identity, check Redis read models, register compute requests, and return cached success or `layout_not_ready`.
  - **Request-path blocking policy:** API request handlers must not run long-running CPU-bound synchronous work. Short bounded async I/O is allowed. Legacy synchronous I/O may be isolated behind bounded async or thread adapters only when justified by an I/O dependency. CPU-bound taxonomy layout computation is not wrapped into FastAPI request handling.
  - **Card-scope data-plane rule:** Card-scope browsing is split into a metadata surface, a viewport-scoped layout slice surface, a node-title surface, and a node-detail surface. The layout slice surface carries backend-computed world coordinates plus local topology for the requested world bounds. The node-title surface carries `title` only for requested node ids. The node-detail surface carries `title`, `content`, and `current_version` only for requested node ids.
  - **Card-scope hydration rule:** Entering a card scope returns metadata and does not include the full one-hop graph, node `title`, or node `content`.
  - **Card-scope title request rule:** Node titles are fetched by explicit node-id batches scoped to the active card scope and are used for viewport-scoped point-title labels.
  - **Card-scope detail request rule:** Node details are fetched by explicit node-id batches scoped to the active card scope; the initial card-scope view payload excludes node `title`, `content`, and `current_version`.
  - **Card-scope read-model rule:** Card-scope browsing uses the authoritative current-assignment table for inner-node membership and one dedicated scope projection table for one-hop edge membership. The projection stores only `(scope_kind, taxonomy_node_id, edge_id)` identity and does not duplicate mutable edge fields such as `strength`.
  - **Read-performance rule:** Taxonomy view read paths must avoid full-graph or full-assignment work when the request scope is smaller. Root, branch node, card-scope metadata, and path-addressed view payloads use API-owned Redis response caches and cached descendant counts or layout metadata derived from current read models. Layout slice, title, and detail reads must use scope-scoped assignment lookups, scope-scoped projection-edge reads, cached backend layout coordinates, viewport-bounded layout slice reads, and node-id-scoped detail reads.

## Persistence Projection

### taxonomy_nodes
- `id`: integer primary key.
- `parent_id`: nullable foreign key to `taxonomy_nodes.id`.
- `name`: non-null text.
- `depth`: non-null integer with `depth >= 0`.
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
- Persisted-node rule:
  - taxonomy rows represent real LCC category nodes only.
  - branch and card-scope behavior is derived from current child rows and current direct assignments.

### node_taxonomy_assignments
- `id`: integer primary key.
- `node_id`: non-null foreign key to persisted knowledge node.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp recording the current assignment write.
- Required constraints:
  - uniqueness over `node_id`.
- Required access paths:
  - indexed lookup by `taxonomy_node_id`.
  - indexed lookup by `(taxonomy_node_id, node_id)` for scope-scoped node membership reads.
- Write-path rule:
  - assignment writes are upserts by `node_id`.
  - moving a node updates the existing row's `taxonomy_node_id` and current assignment timestamp.

### taxonomy_scope_projection_edges
- `scope_kind`: non-null text identifying whether the projection belongs to a real taxonomy node scope or a virtual Unclassified child scope.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `edge_id`: non-null foreign key to `edges.id`.
- Required constraints:
  - primary key over `(scope_kind, taxonomy_node_id, edge_id)`.
- Required access paths:
  - indexed read by `(scope_kind, taxonomy_node_id)`.
  - indexed reverse lookup by `edge_id` for incremental maintenance when an edge changes.
- Read-model rule:
  - one row means the referenced edge belongs to the one-hop projection for the referenced card scope.
  - the table stores only scope-edge membership and does not duplicate `node_a_id`, `node_b_id`, or `strength`.
- Derivation rule:
  - inner nodes come from `node_taxonomy_assignments`.
  - outer nodes are derived at read time from the endpoints of the projected edges after subtracting the inner node set.
- Incremental-maintenance rule:
  - assigning or moving a node refreshes projection rows for affected source and target card scopes.
  - creating an edge inserts projection rows for the card scope of each endpoint node, resulting in one row when both endpoints share a scope and at most two rows otherwise.
  - mutable edge fields such as `strength` are read from `edges` at query time through `edge_id` and are not copied into the projection.

### Taxonomy View Redis Read Model
- Redis stores recomputable taxonomy view read models only. PostgreSQL remains the authoritative source for taxonomy nodes, current assignments, projection-edge membership, knowledge nodes, and edge fields. Cached taxonomy view values may be temporarily stale within their configured TTL windows.
- Branch count read models store descendant card counts by taxonomy node id and support root and branch child filtering without scanning all assignments on every view request.
- Root, branch node, card-scope metadata, and canonical path view read models store validated taxonomy response payloads for short-TTL high-concurrency Graph View reads.
- Card-scope layout read models store backend-computed global world coordinates for the one-hop card graph, layout bounds, layout algorithm version, generated timestamp, and node scope metadata.
- Redis cache keys include a schema or layout algorithm version so incompatible read-model shapes are not reused across implementation changes.
- Root, branch node, card-scope metadata, and canonical path view cache keys follow the API read-model cache namespace and TTL policy defined in `api-read-model-cache.md`.
- Card-scope layout cache keys include the active readable-scale layout algorithm version and explicit scope identity.
- Cache entries expire by TTL and use versioned keys for incompatible shape or algorithm changes.
- Bounded cache misses may be rebuilt from PostgreSQL truth in the request path when they do not require long-running CPU-bound work.
- Missing or expired card-scope layout read models are not computed in the request path. Card-scope metadata and viewport layout reads register or refresh a Redis-backed compute request and return `503 layout_not_ready` with `Retry-After`.
- The taxonomy view layout runtime consumes pending card-scope layout compute requests, builds the full layout from PostgreSQL truth under Redis single-flight state, writes the layout read model, and logs failures.
- Redis single-flight state prevents duplicate expensive recomputations for the same card-scope identity and layout version.
- Redis loss, flush, or expiry must not create drift because every cached value is derived from PostgreSQL truth.

## Operator Structure Mutation Boundary
- Taxonomy structure mutation runs through dedicated operator scripts backed by taxonomy-owned services.
- The root creation/import path creates one `Root` node.
- Operator scripts may create one or more direct real LCC children under an existing scope node.
- Operator scripts reject duplicate sibling names under the same parent.
- Database initialization and migration flows do not auto-import operator taxonomy content.

## Operator Assignment Backfill
- Knowledge nodes without a taxonomy assignment are assigned through a dedicated operator backfill command.
- The command defaults to a read-only dry run and requires an explicit confirmation flag before writing assignments.
- The command ensures `Root` through taxonomy-owned services before applying assignment writes.
- The command inserts assignments only for knowledge nodes that do not already have a `node_taxonomy_assignments` row.
- Existing assignments are never moved by the backfill command.
- Apply mode rebuilds taxonomy scope projection rows after assignment writes so card-scope views read current one-hop edge membership.

## Development Visualization Seed
- Local development may use a dedicated dev-only seed script to reset and recreate placeholder taxonomy branches, placeholder cards, hardcoded graph edges, card-to-taxonomy assignments, and taxonomy scope projection rows for Graph View inspection.
- The development seed script does not call embedding providers and does not participate in production import, migration, ingestion, or classification flows.
- The development seed script must reject non-local database URLs before writing placeholder rows.

## API Contract

### Card-Scope Layout Readiness Error
- HTTP status: `503`.
- Application error code: `layout_not_ready`.
- Response shape follows the global error envelope with `error.code` and `error.message`.
- The response includes `Retry-After` with the accepted retry delay for clients that choose to retry.
- The error applies when a card-scope metadata or viewport layout request targets a valid real or virtual taxonomy scope whose full layout Redis read model is unavailable for the active layout version.
- Returning `layout_not_ready` also registers or refreshes one Redis-backed compute request for the target scope/version.

### Root View Endpoint
- Route: `GET /api/v1/taxonomy/view/root`
- Success payload:
  - no `current_scope` field.
  - `breadcrumb` is an empty array.
  - `children` array for visible direct child scopes of the real `Root`; each item:
    - `scope_kind` with value `taxonomy_node` or `virtual_unclassified`
    - `taxonomy_node_id` for real taxonomy scopes
    - `parent_taxonomy_node_id` for virtual scopes
    - `name`
    - `route_slug`
    - `route_path`
    - `depth`
    - `node_kind` with value `branch` or `card_scope`
    - `descendant_card_count`
- Failure behavior:
  - `404` when the real `Root` node is unavailable.

### Node View Endpoint
- Route: `GET /api/v1/taxonomy/view/nodes/{node_id}`
- Success payload:
  - common envelope:
    - `node_kind`: `branch` or `card_scope`
    - `current_scope` object:
      - `scope_kind` with value `taxonomy_node`
      - `taxonomy_node_id`
      - `parent_taxonomy_node_id`
      - `name`
      - `route_slug`
      - `route_path`
      - `depth`
    - `breadcrumb` array ordered root-to-current, each item:
      - `scope_kind` with value `taxonomy_node`
      - `taxonomy_node_id`
      - `parent_taxonomy_node_id`
      - `name`
      - `route_slug`
      - `route_path`
      - `depth`
  - branch case (`node_kind=branch`):
    - `children` using the same child item shape as root endpoint.
    - real child taxonomy scopes are returned when their descendant subtree contains assigned cards.
    - a virtual `Unclassified` child scope is returned only when the current taxonomy node has direct cards and at least one visible real child taxonomy scope.
  - card-scope case (`node_kind=card_scope`):
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
  - `503 layout_not_ready` per Card-Scope Layout Readiness Error when the node is a card scope and its full layout read model is unavailable.
  - request-shape errors follow global error-governance behavior.

### Path View Endpoint
- Route: `GET /api/v1/taxonomy/view/path/{route_path:path}`
- Request path:
  - `route_path` is a slash-joined canonical LCC slug path excluding the system `Root` segment.
  - appending `/unclassified` addresses a virtual Unclassified card scope under the resolved parent taxonomy node.
  - the path parameter captures nested slash-separated segments.
- Success payload:
  - same response union as `GET /api/v1/taxonomy/view/nodes/{node_id}` for a resolved real taxonomy node.
  - the card-scope response case for a resolved virtual Unclassified scope.
  - response nodes include `route_slug` and `route_path` so clients can navigate only through canonical paths returned by the taxonomy service.
- Failure behavior:
  - `404` when any path segment does not resolve below its current parent.
  - `404` when an `unclassified` path segment does not resolve to a visible virtual Unclassified scope.
  - `404` when taxonomy root is unavailable.
  - `503 layout_not_ready` per Card-Scope Layout Readiness Error when the resolved scope is a card scope and its full layout read model is unavailable.
  - request-shape errors follow global error-governance behavior.

### Card-Scope Layout Viewport Endpoint
- Route: `GET /api/v1/taxonomy/view/card-scopes/layout`
- Request query parameters:
  - `route_path`
  - `min_x`
  - `min_y`
  - `max_x`
  - `max_y`
- Success payload:
  - `route_path`
  - `scope_kind`
  - `taxonomy_node_id` for real taxonomy scopes
  - `parent_taxonomy_node_id` for virtual scopes
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
  - `404` when `route_path` does not resolve to a card scope.
  - `404` when taxonomy root is unavailable.
  - `503 layout_not_ready` per Card-Scope Layout Readiness Error when the full layout read model is unavailable.
  - request-shape errors follow global error-governance behavior.

### Card-Scope Titles Endpoint
- Route: `POST /api/v1/taxonomy/view/card-scopes/titles`
- Request payload:
  - `route_path`
  - `node_ids`: non-empty array of unique positive integers
- Success payload:
  - `nodes` array ordered to match the request `node_ids`; each item:
    - `id`
    - `title`
- Failure behavior:
  - `404` when `route_path` does not resolve to a card scope.
  - `404` when taxonomy root is unavailable.
  - `400` when `node_ids` is empty, contains duplicates, or references a node outside the active card-scope one-hop graph.

### Card-Scope Detail Endpoint
- Route: `POST /api/v1/taxonomy/view/card-scopes/details`
- Request payload:
  - `route_path`
  - `node_ids`: non-empty array of unique positive integers
- Success payload:
  - `nodes` array ordered to match the request `node_ids`; each item:
    - `id`
    - `current_version`
    - `title`
    - `content`
- Failure behavior:
  - `404` when `route_path` does not resolve to a card scope.
  - `404` when taxonomy root is unavailable.
  - `400` when `node_ids` is empty, contains duplicates, or references a node outside the active card-scope one-hop graph.

## Response Ordering Rules
- `breadcrumb` is ordered root-to-current.
- branch `children` are ordered by `name ASC`, tie-break by `id ASC`.
- card-scope layout slice `nodes` are ordered by `id ASC`.
- card-scope layout slice `edges` are deduplicated by undirected pair and ordered by `(source_node_id ASC, target_node_id ASC)`.
- every card-scope layout slice `edges` tuple uses canonical undirected endpoint ordering with `source_node_id < target_node_id`.
- card-scope title `nodes` are ordered to match request `node_ids`.
- card-scope detail `nodes` are ordered to match request `node_ids`.

## Read And Write Responsibilities
- The taxonomy module provides:
  - complete taxonomy-tree reads and direct-child reads;
  - root lookup and path-based virtual Unclassified scope resolution;
  - current assignment lookup for one knowledge node;
  - default assignment directly to `Root`;
  - assignment movement between valid real taxonomy nodes;
  - direct child category creation;
  - cached aggregate descendant counts for branch view payloads;
  - branch/card-scope drill-down view payloads with breadcrumb context;
  - registration of single-flight card-scope layout compute requests;
  - backend-computed global world coordinates for card-scope graph layout through the dedicated taxonomy view layout runtime;
  - viewport-bounded card-scope layout slices;
  - card-scope node-title hydration for explicit node-id batches within one active graph;
  - card-scope node-detail hydration with current version for explicit node-id batches within one active graph.
- The taxonomy module does not provide:
  - AI classification job submission or result consumption;
  - confidence scoring workflows;
  - semantic-map snapshot/tile contracts;
  - frontend camera state, pan/zoom transforms, hover state, selection state, or visual styling.

## Query Performance Projection
- Root and branch descendant counts are served from the Redis taxonomy view read model and recomputed from persisted current assignments on cache miss or expiry.
- The repository layer exposes scope-scoped assignment reads that return only the node ids assigned to one real taxonomy node or virtual Unclassified parent scope.
- Card graph edge expansion reads `edge_id` membership from `taxonomy_scope_projection_edges` for the active scope identity, then joins to `edges` to obtain current endpoints and `strength`.
- Card graph node scope is reconstructed from two sources only: inner membership from `node_taxonomy_assignments` and projected edge endpoints from `taxonomy_scope_projection_edges`.
- Card-scope metadata and viewport layout reads use only cached full layout read models for layout metadata, node membership, and world coordinates.
- Card-scope metadata and viewport layout reads return `layout_not_ready` instead of computing layout when the full layout read model is unavailable.
- The dedicated taxonomy view layout runtime computes stable global world coordinates from the scope-scoped one-hop graph through the deterministic force simulation and stores the derived coordinates in Redis with a TTL-bound eventual-consistency window.
- Card-scope layout viewport reads return only nodes inside requested world bounds plus edges whose endpoints are both in the returned node set.
- Card-scope title hydration validates requested node ids against cached layout membership or scope-scoped projection membership without loading content or current-version data for every node in that graph.
- Card-scope title hydration reads `title` only for the requested node ids after membership validation succeeds.
- Card-scope detail hydration validates requested node ids against cached layout membership or scope-scoped projection membership without loading title/content/current-version data for every node in that graph.
- Card-scope detail hydration reads `title`, `content`, and `current_version` only for the requested node ids after membership validation succeeds.
- Taxonomy read performance behavior remains inside the taxonomy and knowledge-graph repository/service boundaries while the taxonomy view HTTP contracts expose backend-owned branch filtering and viewport-bounded card-scope layout slices.

## Validation
- **Checks:**
  - Taxonomy bootstrap creates exactly one `Root` node.
  - Storage rejects a second `taxonomy_nodes` row with `parent_id IS NULL`.
  - Taxonomy bootstrap creates the persisted root row with `name='Root'` and `depth=0`.
  - Regular child creation creates only the requested category nodes.
  - Sibling reads return `ORDER BY name ASC`.
  - One knowledge node has exactly one current assignment row.
  - Assignment moves update the current taxonomy node without creating duplicate rows.
  - New ingestion-created nodes receive assignment directly to `Root`.
  - Operator backfill assigns only unassigned knowledge nodes directly to `Root`.
  - `GET /api/v1/taxonomy/view/root` returns non-empty direct children of `Root` with `breadcrumb=[]`.
  - `GET /api/v1/taxonomy/view/nodes/{id}` returns correct discriminated payload for branch or card scope.
  - Canonical route slug generation preserves ASCII letters and digits, lowercases names, collapses non-alphanumeric runs to single hyphens, and trims leading and trailing hyphens.
  - Taxonomy import and operator child creation reject sibling names that derive the same route slug.
  - `GET /api/v1/taxonomy/view/path/{route_path:path}` resolves nested canonical route paths to the same discriminated payload as the resolved node id.
  - `GET /api/v1/taxonomy/view/path/{route_path:path}` returns `404` when any path segment is missing below its current parent.
  - Path view resolves visible virtual Unclassified scopes through the fixed `unclassified` route segment below their parent taxonomy route path.
  - Card-scope node and path view payloads return `503 layout_not_ready` with `Retry-After` when the active full layout read model is unavailable.
  - Concurrent card-scope metadata requests for the same scope/version register at most one pending or running layout compute request.
  - Branch node view payloads omit direct children whose descendant subtree has zero assigned cards.
  - Branch node view payloads include a virtual Unclassified child only when the current node has both direct card assignments and visible real child category scopes.
  - Branch node view payloads omit a virtual Unclassified child when the current node has direct card assignments but no visible real child category scopes.
  - Card-scope node view payloads return metadata for backend layout consumption without returning the full one-hop graph.
  - `GET /api/v1/taxonomy/view/card-scopes/layout` returns backend-computed world coordinates and local edges for the requested world bounds.
  - `GET /api/v1/taxonomy/view/card-scopes/layout` returns `503 layout_not_ready` with `Retry-After` when the active full layout read model is unavailable.
  - API request handlers do not call the CPU-bound card-scope layout simulation.
  - The taxonomy view layout runtime consumes pending card-scope layout compute requests and writes full layout read models.
  - Card-scope layout generation responds to edge strength in the deterministic force geometry while remaining stable for identical inputs and layout algorithm version.
  - `POST /api/v1/taxonomy/view/card-scopes/titles` returns `title` only for requested node ids inside the active card-scope graph.
  - `POST /api/v1/taxonomy/view/card-scopes/details` returns `title`, `content`, and `current_version` only for requested node ids inside the active card-scope graph.
  - Card-scope edge reads use the scope projection table and stay scoped to the requested graph.
  - Card-scope detail hydration does not require loading title/content/current-version data for every node in the expanded one-hop graph.
  - Scope-scoped assignment lookups use indexed access by `taxonomy_node_id`.
- **Evidence:**
  - Passing import/repository/service tests and API contract tests for taxonomy structure, assignment movement, and taxonomy view endpoints.
