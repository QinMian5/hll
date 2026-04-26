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
- `taxonomy_leaf_projection_edges`
- `taxonomy_classification_jobs`
- `taxonomy_classification_webhook_events`
- `taxonomy_classification_webhook_wakeups`

### Nodes
- `id`: integer primary key.
- `title`: non-null text.
- `content`: non-null text.
- `embedding`: non-null `Vector(1536)`.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.

### Edges
- `id`: integer primary key.
- `node_a_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `node_b_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `strength`: non-null float.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.
- Required constraints:
  - canonical unordered pair: `node_a_id < node_b_id`.
  - normalized strength range: `0.0 <= strength <= 1.0`.
  - unordered-pair uniqueness over `(node_a_id, node_b_id)`.

### Adjacency
- Composite primary key: `(node_id, edge_id)`.
- `node_id`: foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `edge_id`: foreign key to `edges.id` with `ondelete="CASCADE"`.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.
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
  - partial unique index enforcing at most one row with `parent_id IS NULL`
- Required read-order rule:
  - sibling rows selected with `ORDER BY name ASC`.
- Root rule:
  - exactly one row represents the real `Root` node; storage enforces at most one root row and taxonomy bootstrap/service code ensures root availability.
- System bucket rule:
  - each regular taxonomy node has a direct child named `Unclassified` with `is_leaf = true`.

### Node Taxonomy Assignments
- `id`: integer primary key.
- `node_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp.
- Required constraints:
  - uniqueness over `node_id`.
- Required trigger rule:
  - insert/update rejected unless `taxonomy_node_id` points to `taxonomy_nodes.is_leaf = true`.
- Write semantics:
  - inserts create the current assignment for a node.
  - updates move the current assignment for a node.
- Trigger implementation rule:
  - leaf-only assignment trigger is maintained through one dedicated migration scoped to trigger/function DDL.

### Taxonomy Leaf Projection Edges
- Composite primary key: `(leaf_id, edge_id)`.
- `leaf_id`: non-null foreign key to `taxonomy_nodes.id` with `ondelete="CASCADE"`.
- `edge_id`: non-null foreign key to `edges.id` with `ondelete="CASCADE"`.
- Required indexes:
  - index on `edge_id`.
- Projection rule:
  - rows store leaf-edge membership only.
  - mutable edge values are read from `edges`.

### Taxonomy Classification Jobs
- `id`: integer primary key.
- `scope_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `source_unclassified_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `node_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `job_id`: nullable integer identifier assigned by `job-queue-mcp` after the local
  active submission intent is committed.
- `terminal_state`: nullable text.
- `processed_at`: nullable timestamp with timezone.
- `target_payload`: nullable JSON payload for accepted valid result target snapshots.
- `last_error`: nullable text.
- `created_at`: non-null timestamp with timezone.
- `updated_at`: non-null timestamp with timezone.
- Required constraints:
  - uniqueness over non-null `job_id` values.
  - partial uniqueness over `(scope_node_id, source_unclassified_node_id, node_id)` for active outstanding rows only, where `processed_at IS NULL` and `terminal_state IS NULL`.
- Active-linkage rule:
  - processed accepted results, invalid accepted results recorded as local processing errors, and terminal non-accepted rows do not block a later operator submission for the same scope/source/card.

### Taxonomy Classification Webhook Events
- `id`: integer primary key.
- `event_id`: non-null text.
- `event_type`: non-null text.
- `job_id`: non-null integer.
- `queue_name`: non-null text.
- `submission_id`: nullable integer.
- `terminal_state`: nullable text.
- `occurred_at`: non-null timestamp with timezone.
- `payload`: non-null JSON payload.
- `processed_at`: nullable timestamp with timezone.
- `last_error`: nullable text.
- `created_at`: non-null timestamp with timezone.
- `updated_at`: non-null timestamp with timezone.
- Required constraints:
  - uniqueness over `event_id`.
- Required indexes:
  - pending-event lookup by `processed_at` and creation order.

### Taxonomy Classification Webhook Wakeups
- `id`: integer primary key.
- `event_id`: non-null foreign key to taxonomy classification webhook event identity.
- `created_at`: non-null timestamp with timezone.
- Required constraints:
  - uniqueness over `event_id`.

## Integrity and Coupling Rules
- Persistence constraints enforce undirected edge semantics at storage level.
- One canonical edge row exists for one unordered node pair.
- Taxonomy tree truth, current assignment truth, and taxonomy classification orchestration state remain outside `knowledge_graph` table ownership.
- Constraint and index naming follows shared SQLAlchemy metadata conventions unless fixed semantic names are explicitly required.

## Validation
- Metadata includes all accepted persistence models before migration autogeneration.
- Generated/applied schema enforces all required constraints and indexes.
- Generated/applied schema enforces taxonomy leaf-only assignment trigger.
- Generated/applied schema enforces taxonomy root uniqueness.
- Generated/applied schema allows later classification resubmission after a previous job for the same scope/source/card is locally processed or terminal.
- Vector type validity depends on PostgreSQL `vector` extension availability before dependent migration.
- Migration ordering/lifecycle checks are governed by `10-migration-lifecycle-governance`.
