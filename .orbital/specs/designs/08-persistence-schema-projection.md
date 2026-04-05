---
abstract: Persistence schema projection for mapping accepted domain modules into SQLAlchemy and PostgreSQL structures.
out_of_scope: Runtime session lifecycle, migration execution policy, and API transport schema design.
---

# Design: 08-persistence-schema-projection

## Active Truth Policy
- This document defines only current persistence-schema decisions.
- Superseded schema decisions are removed from active text.

## Context
- **Purpose:** Project accepted domain-module semantics into concrete persistence structures.
- **Scope/Boundaries:** Covers table/column mapping, constraints, indexes, triggers, and vector field semantics for persistence.
- **Related Requirements:** R-002, R-004, R-005, R-006.
- **Upstream Design Dependency:** `02-core-domain-model` is the semantic source of truth.

## Projection Boundary
- The persistence projection for V1 is represented by SQLAlchemy models under the owning backend modules.
- Persistence projection uses shared metadata from `shared/db/base.py`.
- The projection contains only persistence semantics and must not include API response shaping rules.

## V1 Persistence Projection

### Tables
- `nodes`
- `edges`
- `adjacency`
- `semantic_map_snapshots`
- `semantic_map_region_tiles`
- `taxonomy_nodes`
- `node_taxonomy_assignments`

### Nodes
- `id`: integer primary key.
- `title`: non-null text.
- `content`: non-null text.
- `embedding`: non-null `Vector(1536)`.

### Edges
- `id`: integer primary key.
- `node_a_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `node_b_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `strength`: non-null float.
- Required constraints:
  - canonical unordered pair: `node_a_id < node_b_id`.
  - normalized strength range: `0.0 <= strength <= 1.0`.
  - unordered-pair uniqueness over `(node_a_id, node_b_id)`.

### Adjacency
- Composite primary key: `(node_id, edge_id)`.
- `node_id`: foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `edge_id`: foreign key to `edges.id` with `ondelete="CASCADE"`.
- Required secondary indexes:
  - index on `node_id`.
  - index on `edge_id`.

### Semantic Map Snapshots
- `id`: integer primary key.
- `version`: non-null unique text.
- `schema_version`: non-null text.
- `built_at`: non-null timestamp.
- `current`: non-null boolean.
- `world_bounds`: non-null JSON array representing `[min_x, min_y, max_x, max_y]`.
- `tile_size`: non-null integer.
- `max_zoom`: non-null integer.
- `default_view`: non-null JSON object.
- `default_semantic_level`: non-null integer.

### Semantic Map Region Tiles
- `id`: integer primary key.
- `snapshot_id`: non-null foreign key to `semantic_map_snapshots.id` with `ondelete="CASCADE"`.
- `semantic_level`: non-null integer.
- `tile_z`: non-null integer.
- `tile_x`: non-null integer.
- `tile_y`: non-null integer.
- `tile_bounds`: non-null JSON array representing `[min_x, min_y, max_x, max_y]`.
- `region_count`: non-null integer.
- `label_count`: non-null integer.
- `regions`: non-null JSON array.
- `labels`: non-null JSON array.
- Required constraints:
  - uniqueness over `(snapshot_id, semantic_level, tile_z, tile_x, tile_y)`.

### Taxonomy Nodes
- `id`: integer primary key.
- `parent_id`: nullable foreign key to `taxonomy_nodes.id`.
- `name`: non-null text.
- `depth`: non-null integer.
- `is_leaf`: non-null boolean.
- Required constraints:
  - `depth >= 0`.
  - uniqueness over `(parent_id, name)`.
- Required read-order rule:
  - sibling rows are selected with `ORDER BY name ASC`.

### Node Taxonomy Assignments
- `id`: integer primary key.
- `node_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp.
- Required constraints:
  - uniqueness over `node_id`.
- Required trigger rule:
  - insert and update operations are rejected unless `taxonomy_node_id` points to a taxonomy row where `is_leaf = true`.
- Trigger implementation rule:
  - the leaf-only assignment trigger is added through one dedicated hand-authored migration that is scoped only to that trigger/function DDL.

## Integrity and Coupling Rules
- Persistence constraints enforce undirected edge semantics at storage level.
- Persistence projection must remain deterministic with one canonical edge row for one unordered pair.
- Taxonomy tree truth and final taxonomy-leaf assignment truth are stored outside `knowledge_graph` tables and do not mutate the graph-domain persistence model.
- Constraint and index naming follows shared SQLAlchemy metadata naming conventions unless a schema rule explicitly requires a fixed semantic name.

## Validation
- Metadata includes all accepted persistence models before migration autogeneration.
- Generated/applied schema enforces all required constraints and indexes.
- Generated/applied schema enforces the taxonomy leaf-only assignment trigger.
- Vector field type is valid only when the PostgreSQL `vector` extension is available before dependent schema migration.
- Migration ordering and lifecycle checks are governed by `10-migration-lifecycle-governance`.
