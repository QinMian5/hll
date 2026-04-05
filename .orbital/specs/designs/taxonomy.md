---
abstract: Taxonomy module design for authoritative LCC tree storage and final node-to-leaf assignment truth.
out_of_scope: LLM classification orchestration, candidate ranking workflows, and semantic-map rendering implementation.
---

# Design: taxonomy

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy` module that stores the authoritative LCC tree and the final leaf-level classification binding for knowledge nodes.
- **Scope/Boundaries:** Covers taxonomy ownership, persistence shape, import boundaries, integrity constraints, and read-side responsibilities. Excludes classifier orchestration, confidence workflows, and semantic-map rendering behavior.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth stays isolated by owner, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** LCC is a single authoritative taxonomy tree stored in the database; each knowledge node can bind to exactly one taxonomy leaf; taxonomy bootstrap happens only through a dedicated import script and not through database initialization.
- **Update Rule:** Requirement-level constraints remain stable while taxonomy structure, table ownership, and import rules are maintained here as the implementation-facing source of truth.

## Design Approach
- **Approach:** Add a dedicated backend `taxonomy` module that owns taxonomy tree persistence and final leaf assignment truth while keeping `knowledge_graph` persistence unchanged.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy` owns taxonomy tree reads, final node assignment reads/writes, taxonomy DTO/port contracts, and taxonomy import orchestration.
  - **Authoritative taxonomy source:** The persisted taxonomy tree is the runtime/system truth. `human_workspace/LCC.yaml` is only the operator-maintained import input for bootstrap.
  - **Tree stability model:** The taxonomy is treated as one single, effectively stable tree. Active behavior does not include versioning, merge/update import, or repeatable synchronization against YAML.
  - **Classification result model:** Each knowledge node binds to exactly one final taxonomy leaf. Workflow state, candidate classes, confidence scores, and review status are not part of the accepted persistence shape.
  - **Map-structure role:** Taxonomy provides the high-level structural truth for semantic-map browsing. Semantic-map rendering may consume embeddings for local layout, but it does not define top-level class hierarchy independently of taxonomy.

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
- `node_id`: non-null foreign key to the persisted knowledge node.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp.
- Required constraints:
  - uniqueness over `node_id`.

### Trigger Rule
- Inserts and updates on `node_taxonomy_assignments` must be rejected unless `taxonomy_node_id` points to a row where `taxonomy_nodes.is_leaf = true`.
- The leaf-only assignment trigger is implemented through one dedicated hand-authored migration that contains only the trigger/function DDL and does not mix unrelated schema changes.

## Import Boundary
- Taxonomy bootstrap is executed through a dedicated operator script.
- The import script reads `human_workspace/LCC.yaml`, computes `depth`, computes `is_leaf`, and inserts the taxonomy tree into `taxonomy_nodes`.
- The import script fails immediately when `taxonomy_nodes` already contains any rows.
- The import script does not merge, update, or reconcile an existing taxonomy tree.
- Database initialization and migration flows do not auto-import taxonomy content.

## Read Responsibilities
- The taxonomy module provides:
  - complete taxonomy-tree reads;
  - direct-child reads for one taxonomy node;
  - lookup of the final assigned taxonomy leaf for one knowledge node;
  - aggregate counts that can be consumed by downstream product surfaces.
- The taxonomy module does not provide:
  - candidate generation workflows;
  - confidence computation;
  - human review workflow state;
  - semantic-map visualization logic.

## Validation
- **Checks:**
  - Taxonomy tree import succeeds only into an empty taxonomy store.
  - Imported rows have correct `depth` and `is_leaf` values.
  - Sibling reads return nodes ordered by `name ASC`.
  - A knowledge node cannot have more than one taxonomy assignment.
  - Assignment writes targeting a non-leaf taxonomy node are rejected by database trigger.
- **Evidence:**
  - Passing import tests for empty-store success and non-empty-store failure.
  - Passing repository/service tests for tree reads and assignment reads.
  - Passing database-level tests for unique-assignment and leaf-only trigger enforcement.
