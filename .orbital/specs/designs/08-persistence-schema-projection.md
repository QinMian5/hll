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
- `card_versions`
- `card_suggested_edits`
- `edges`
- `adjacency`
- `ingestion_requests`
- `taxonomy_nodes`
- `node_taxonomy_assignments`
- `taxonomy_scope_projection_edges`
- `taxonomy_classification_jobs`
- `taxonomy_classification_webhook_events`
- `taxonomy_classification_webhook_wakeups`

### Development Bootstrap Snapshot
- `scripts/export-prod-api-bootstrap-snapshot.sh` exports a production data-only snapshot for development bootstrap.
- The export is read-only against production PostgreSQL and is scoped to the API tables listed in this section.
- `alembic_version` is excluded; Alembic migrations remain the schema source of truth.
- `make dev-up` invokes `scripts/bootstrap-dev-api-from-prod-snapshot.sh` before starting the development Compose stack.
- `scripts/bootstrap-dev-api-from-prod-snapshot.sh` targets `infra/env/.env.dev`, runs development migrations, stops development API writer and taxonomy layout services, truncates the scoped API tables with `RESTART IDENTITY CASCADE`, restores the snapshot, and clears Redis-derived read models.
- The snapshot preserves current card IDs, titles, content, embeddings, edge relationships, taxonomy nodes, node taxonomy assignments, taxonomy projection edges, ingestion request rows, and taxonomy classification orchestration rows.

### Nodes
- `id`: integer primary key.
- `title`: non-null text.
- `content`: non-null text.
- `current_version`: non-null integer, server default `1`.
- `embedding`: non-null `Vector(1536)`.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.
- Required constraints:
  - `current_version >= 1`

### Card Versions
- `id`: integer primary key.
- `node_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `version`: non-null integer.
- `title`: non-null text.
- `content`: non-null text.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- Required constraints:
  - `version >= 1`
  - uniqueness over `(node_id, version)`
- Required indexes:
  - index on `node_id`
- Version rule:
  - `version` is scoped to one node.
  - `nodes.current_version` equals the highest `card_versions.version` for that node.

### Card Suggested Edits
- `id`: integer primary key.
- `node_id`: non-null integer participating in the base-version foreign key.
- `base_version`: non-null integer.
- `suggested_title`: non-null text.
- `suggested_content`: non-null text.
- `suggested_by_user_id`: non-null text containing the authenticated Logto user id.
- `status`: non-null text, server default `pending`.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.
- Required constraints:
  - composite foreign key `(node_id, base_version)` to `card_versions(node_id, version)` with `ondelete="CASCADE"`
  - `base_version >= 1`
  - status in `pending`, `accepted`, `rejected`
- Required indexes:
  - index on `node_id`
  - index on `suggested_by_user_id`
  - index on `status`

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
- Required constraints:
  - `depth >= 0`
  - uniqueness over `(parent_id, name)`
  - unique partial index over `(parent_id, lower(name))` where `parent_id IS NOT NULL`, preventing same-level child names that differ only by case
  - partial unique index enforcing at most one row with `parent_id IS NULL`
- Required read-order rule:
  - sibling rows selected with `ORDER BY name ASC`.
- Root rule:
  - exactly one row represents the real `Root` node; storage enforces at most one root row and taxonomy bootstrap/service code ensures root availability.
- Persisted-node rule:
  - taxonomy rows represent real LCC category nodes only.
  - branch and card-scope behavior is derived by the taxonomy service from current child rows and current direct assignments.

### Node Taxonomy Assignments
- `id`: integer primary key.
- `node_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id`.
- `assigned_at`: non-null timestamp.
- Required constraints:
  - uniqueness over `node_id`.
- Write semantics:
  - inserts create the current assignment for a node.
  - updates move the current assignment for a node.

### Taxonomy Scope Projection Edges
- Composite primary key: `(scope_kind, taxonomy_node_id, edge_id)`.
- `scope_kind`: non-null text identifying whether the projection belongs to a real taxonomy node scope or a virtual Unclassified child scope.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id` with `ondelete="CASCADE"`.
- `edge_id`: non-null foreign key to `edges.id` with `ondelete="CASCADE"`.
- Required indexes:
  - index on `edge_id`.
  - index on `(scope_kind, taxonomy_node_id)`.
- Projection rule:
  - rows store card-scope edge membership only.
  - mutable edge values are read from `edges`.

### Ingestion Requests
- `id`: integer primary key and public `ingestion_id` returned by `POST /api/v1/cards`.
- `idempotency_key`: nullable text.
- `payload_hash`: non-null 64-character SHA-256 hash of the normalized accepted payload.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- Required indexes:
  - partial unique index on `idempotency_key` where `idempotency_key IS NOT NULL`
- Write semantics:
  - every newly accepted ingestion request inserts one append-only row before queue dispatch
  - submissions without a non-empty `Idempotency-Key` store `NULL` and always allocate independent integer ids
  - same non-empty idempotency key and same payload hash reuses the existing row id through repository-owned atomic get-or-create semantics without enqueueing another task
  - same non-empty idempotency key and different payload hash is rejected by the ingestion service before enqueueing
  - queue publish failure before accepted-request completion rolls back the inserted row

### Taxonomy Classification Jobs
- `id`: integer primary key.
- `scope_node_id`: non-null foreign key to `taxonomy_nodes.id`.
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
  - partial unique index on `job_id` where `job_id IS NOT NULL`.
  - partial uniqueness over `(scope_node_id, node_id)` for active outstanding rows only, where `processed_at IS NULL` and `terminal_state IS NULL`.
- Active-linkage rule:
  - processed accepted results, invalid accepted results recorded as local processing errors, and terminal non-accepted rows do not block a later operator submission for the same scope/card.

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
- Write semantics:
  - webhook intake uses repository-owned atomic insert-on-conflict semantics for `event_id`.
  - duplicate webhook deliveries return the existing event row without creating another wakeup.
- Required indexes:
  - pending-event lookup by `processed_at` and creation order.

### Taxonomy Classification Webhook Wakeups
- `id`: integer primary key.
- `event_id`: non-null foreign key to taxonomy classification webhook event identity.
- `created_at`: non-null timestamp with timezone.
- Required constraints:
  - uniqueness over `event_id`.

### Taxonomy Classification Projection Refresh Requests
- Composite primary key: `(scope_kind, taxonomy_node_id)`.
- `scope_kind`: non-null text identifying whether the refresh belongs to a real taxonomy node scope or a virtual Unclassified child scope.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id` with `ondelete="CASCADE"`.
- `last_error`: nullable text.
- `created_at`: non-null timestamp with timezone.
- `updated_at`: non-null timestamp with timezone.
- Required indexes:
  - pending refresh lookup by `(updated_at, scope_kind, taxonomy_node_id)`.
- Write semantics:
  - assignment movement inserts or updates one dirty refresh request for each affected scope identity.
  - successful refresh deletes only the refreshed scope request.
  - failed refresh leaves the request retryable with `last_error` populated.

## Integrity and Coupling Rules
- Persistence constraints enforce undirected edge semantics at storage level.
- One canonical edge row exists for one unordered node pair.
- Card current projection, formal version history, and suggested edits remain inside `knowledge_graph` table ownership.
- Taxonomy tree truth, current assignment truth, and taxonomy classification orchestration state remain outside `knowledge_graph` table ownership.
- Constraint and index naming follows shared SQLAlchemy metadata conventions unless fixed semantic names are explicitly required.

## Validation
- Metadata includes all accepted persistence models before migration autogeneration.
- Generated/applied schema enforces all required constraints and indexes.
- Generated/applied schema enforces taxonomy root uniqueness.
- Generated/applied schema enforces card version uniqueness, suggestion base-version references, and suggestion status values.
- Generated/applied schema allows later classification resubmission after a previous job for the same scope/card is locally processed or terminal.
- Vector type validity depends on PostgreSQL `vector` extension availability before dependent migration.
- Migration ordering/lifecycle checks are governed by `10-migration-lifecycle-governance`.
