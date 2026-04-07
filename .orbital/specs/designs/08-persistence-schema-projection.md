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
- **Scope/Boundaries:** Covers table/column mapping, constraints, indexes, triggers, and vector semantics for persistence.
- **Related Requirements:** R-002, R-004, R-005, R-006.
- **Upstream Design Dependency:** `02-core-domain-model` is semantic source of truth.

## Projection Boundary
- Persistence projection is represented by SQLAlchemy models under owning backend modules.
- Projection uses shared metadata from `shared/db/base.py`.
- Projection contains persistence semantics only and excludes API response-shaping rules.

## V1 Persistence Projection

### Tables
- `nodes`
- `edges`
- `adjacency`
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
- Required indexes:
  - index on `node_id`
  - index on `edge_id`

### Taxonomy Nodes
- `id`: integer primary key.
- `parent_id`: nullable foreign key to `taxonomy_nodes.id`.
- `name`: non-null text.
- `depth`: non-null integer.
- `is_leaf`: non-null boolean.
- Required constraints:
  - `depth >= 0`
  - uniqueness over `(parent_id, name)`
- Required read-order rule:
  - sibling rows selected with `ORDER BY name ASC`.

### Node Taxonomy Assignments
- `id`: integer primary key.
- `node_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp.
- Required constraints:
  - uniqueness over `node_id`.
- Required trigger rule:
  - insert/update rejected unless `taxonomy_node_id` points to `taxonomy_nodes.is_leaf = true`.
- Trigger implementation rule:
  - leaf-only assignment trigger is maintained through one dedicated migration scoped to trigger/function DDL.

## Integrity and Coupling Rules
- Persistence constraints enforce undirected edge semantics at storage level.
- One canonical edge row exists for one unordered node pair.
- Taxonomy tree truth and final assignment truth remain outside `knowledge_graph` table ownership.
- Constraint and index naming follows shared SQLAlchemy metadata conventions unless fixed semantic names are explicitly required.

## Validation
- Metadata includes all accepted persistence models before migration autogeneration.
- Generated/applied schema enforces all required constraints and indexes.
- Generated/applied schema enforces taxonomy leaf-only assignment trigger.
- Vector type validity depends on PostgreSQL `vector` extension availability before dependent migration.
- Migration ordering/lifecycle checks are governed by `10-migration-lifecycle-governance`.
