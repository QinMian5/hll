---
abstract: Persistence schema projection for mapping the core domain model into SQLAlchemy and PostgreSQL structures.
out_of_scope: Runtime session lifecycle, migration execution policy, and API transport schema design.
---

# Design: 08-persistence-schema-projection

## Active Truth Policy
- This document defines only current persistence-schema decisions.
- Superseded schema decisions are removed from active text.

## Context
- **Purpose:** Project core domain semantics into concrete persistence structures.
- **Scope/Boundaries:** Covers table/column mapping, constraints, indexes, and vector field semantics for persistence.
- **Related Requirements:** R-002, R-004, R-005, R-006.
- **Upstream Design Dependency:** `02-core-domain-model` is the semantic source of truth.

## Projection Boundary
- The persistence projection for V1 is represented by SQLAlchemy models under `modules/knowledge/model.py`.
- Persistence projection uses shared metadata from `shared/db/base.py`.
- The projection contains only persistence semantics and must not include API response shaping rules.

## V1 Persistence Projection

### Tables
- `nodes`
- `edges`
- `adjacency`

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

## Integrity and Coupling Rules
- Persistence constraints enforce undirected edge semantics at storage level.
- Persistence projection must remain deterministic with one canonical edge row for one unordered pair.
- Schema projection must not duplicate domain semantics in additional tables that are not part of V1 scope.
- Constraint and index naming follows shared SQLAlchemy metadata naming conventions unless a schema rule explicitly requires a fixed semantic name.

## Validation
- Metadata includes `nodes`, `edges`, and `adjacency` before migration autogeneration.
- Generated/applied schema enforces all required constraints and indexes.
- Vector field type is valid only when the PostgreSQL `vector` extension is available before dependent schema migration.
- Migration ordering and lifecycle checks are governed by `10-migration-lifecycle-governance`.
