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
- **Related Requirements:** R-002, R-004, R-005, R-006, R-008.
- **Upstream Design Dependency:** `02-core-domain-model` is semantic source of truth.

## Projection Boundary
- Persistence projection is represented by SQLAlchemy models under owning backend modules.
- Projection uses shared metadata from `shared/db/base.py`.
- Projection contains persistence semantics only and excludes API response-shaping rules.

## V1 Persistence Projection

### Tables
- `nodes`
- `card_versions`
- `workspace_roles`
- `card_proposals`
- `proposal_apply_audits`
- `edges`
- `adjacency`
- `ingestion_requests`
- `taxonomy_nodes`
- `node_taxonomy_assignments`
- `taxonomy_scope_projection_edges`
- `taxonomy_card_scope_layouts`
- `taxonomy_card_scope_layout_compute_requests`
- `taxonomy_classification_jobs`
- `taxonomy_classification_continuation_requests`
- `taxonomy_classification_webhook_events`
- `taxonomy_classification_webhook_wakeups`

### Development Bootstrap Snapshot
- `scripts/export-prod-api-bootstrap-snapshot.sh` exports a production data-only snapshot for development bootstrap.
- The export is read-only against production PostgreSQL and is scoped to the API tables listed in this section.
- `alembic_version` is excluded; Alembic migrations remain the schema source of truth.
- `make dev-up` invokes `scripts/bootstrap-dev-api-from-prod-snapshot.sh` before starting the development Compose stack.
- `scripts/bootstrap-dev-api-from-prod-snapshot.sh` targets `infra/env/.env.dev`, runs development migrations, stops development API writer and taxonomy layout services, truncates the scoped API tables with `RESTART IDENTITY CASCADE`, restores the snapshot, and clears Redis-derived read models.
- The snapshot preserves current card IDs, titles, content, embeddings, edge relationships, taxonomy nodes, node taxonomy assignments, taxonomy projection edges, durable taxonomy card-scope layouts, ingestion request rows, and taxonomy classification orchestration rows.

### Nodes
- `id`: integer primary key.
- `title`: non-null text.
- `content`: non-null text.
- `current_version`: non-null integer, server default `1`.
- `embedding`: non-null `Vector(1536)`.
- `lifecycle_state`: non-null text identifying active or archived card state.
- `search_vector`: non-null persisted weighted PostgreSQL full-text search vector derived from title and content.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.
- Required constraints:
  - `current_version >= 1`
- Required indexes:
  - GIN index on `search_vector`.
  - HNSW index on `embedding` using the pgvector cosine-distance operator class.

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

### Workspace Roles
- `id`: integer primary key.
- `user_id`: non-null text containing the Logto user id.
- `role`: non-null text.
- `granted_by_user_id`: non-null text containing the granting Logto user id or operator principal.
- `granted_at`: non-null timestamp with timezone.
- `revoked_by_user_id`: nullable text containing the revoking Logto user id or operator principal.
- `revoked_at`: nullable timestamp with timezone.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.
- Required constraints:
  - role in `reviewer`, `admin`
  - active role uniqueness for `(user_id, role)` where `revoked_at IS NULL`
- Required indexes:
  - index on `user_id`
  - index on `role`

### Card Proposals
- `id`: integer primary key.
- `proposal_type`: non-null text.
- `status`: non-null text.
- `submitted_by_user_id`: non-null text containing the authenticated Logto user id.
- `reason`: non-null text explaining why the contributor recommends the proposed change.
- `reviewed_by_user_id`: nullable text containing the reviewer Logto user id.
- `review_note`: nullable text.
- `payload`: non-null structured proposal payload.
- `payload` for delete proposals carries target node id, base version, target title, and target content from the referenced formal card version.
- `created_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`.
- `updated_at`: non-null timestamp with timezone, server default `CURRENT_TIMESTAMP`, auto-refreshed on row update.
- `reviewed_at`: nullable timestamp with timezone.
- Required constraints:
  - proposal type in `create`, `edit`, `delete`
  - status in `pending_review`, `accepted_applied`, `rejected`, `withdrawn`
  - reason is not blank after trimming whitespace
- Required indexes:
  - index on `submitted_by_user_id`
  - index on `reviewed_by_user_id`
  - index on `status`
  - index on `proposal_type`

### Proposal Apply Audits
- `id`: integer primary key.
- `proposal_id`: non-null foreign key to `card_proposals.id`.
- `reviewer_user_id`: non-null text containing the reviewer Logto user id.
- `proposal_type`: non-null text.
- `affected_node_ids`: non-null structured list of affected node ids.
- `created_versions`: non-null structured list of formal card versions created by the apply operation.
- `archive_outcome`: nullable structured outcome for archive operations.
- `review_note`: nullable text.
- `applied_at`: non-null timestamp with timezone.
- Required indexes:
  - index on `proposal_id`
  - index on `reviewer_user_id`
  - index on `proposal_type`

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

### Taxonomy Card-Scope Layouts
- `id`: integer primary key.
- `scope_kind`: non-null text identifying whether the layout belongs to a real taxonomy node scope or a virtual Unclassified child scope.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id` with `ondelete="CASCADE"`.
- `layout_version`: non-null text identifying the active backend layout algorithm and payload shape.
- `input_fingerprint`: non-null text containing the SHA-256 fingerprint of the graph membership, scoped node roles, projected edges, and edge strengths used to build the layout.
- `layout_payload`: non-null JSON payload containing the full card-scope layout read model.
- `generated_at`: non-null timestamp with timezone copied from the layout payload.
- `created_at`: non-null timestamp with timezone.
- `updated_at`: non-null timestamp with timezone.
- Required constraints:
  - scope kind in `taxonomy_node`, `virtual_unclassified`.
  - uniqueness over `(scope_kind, taxonomy_node_id, layout_version)`.
- Required indexes:
  - index on `(scope_kind, taxonomy_node_id)`.
  - index on `input_fingerprint`.
- Read-model rule:
  - each row stores the latest durable layout available for one scope and layout algorithm version.
  - the API may serve a row whose `input_fingerprint` differs from the current graph input fingerprint and marks that response as refreshing.
  - successful background compute replaces the row atomically with the current input fingerprint and layout payload.

### Taxonomy Card-Scope Layout Compute Requests
- `id`: integer primary key.
- `scope_kind`: non-null text identifying whether the request targets a real taxonomy node scope or a virtual Unclassified child scope.
- `taxonomy_node_id`: non-null foreign key to `taxonomy_nodes.id` with `ondelete="CASCADE"`.
- `layout_version`: non-null text identifying the target backend layout algorithm and payload shape.
- `input_fingerprint`: non-null text identifying the graph input fingerprint requested for computation.
- `status`: non-null text.
- `attempt_count`: non-null integer.
- `last_error`: nullable text.
- `requested_at`: non-null timestamp with timezone.
- `claimed_at`: nullable timestamp with timezone.
- `completed_at`: nullable timestamp with timezone.
- `failed_at`: nullable timestamp with timezone.
- `created_at`: non-null timestamp with timezone.
- `updated_at`: non-null timestamp with timezone.
- Required constraints:
  - scope kind in `taxonomy_node`, `virtual_unclassified`.
  - status in `pending`, `running`, `succeeded`, `failed`.
  - `attempt_count >= 0`.
  - uniqueness over `(scope_kind, taxonomy_node_id, layout_version)`.
- Required indexes:
  - index on `(status, requested_at)`.
  - index on `(scope_kind, taxonomy_node_id)`.
- Singleflight rule:
  - the API records at most one compute request row for each scope and layout version.
  - concurrent requests for the same scope, layout version, and input fingerprint reuse the pending or running request.
  - a later request may replace a succeeded or failed request row with a pending request for the current input fingerprint.
  - a running request whose claim timestamp exceeds the accepted recovery window may be replaced by a pending request for the current input fingerprint.
  - the taxonomy view layout runtime claims pending rows with row-level locking and skip-locked semantics.

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

### Taxonomy Classification Continuation Requests
- `id`: integer primary key.
- `scope_node_id`: non-null foreign key to `taxonomy_nodes.id` with `ondelete="CASCADE"`.
- `node_id`: non-null foreign key to `nodes.id` with `ondelete="CASCADE"`.
- `source_job_id`: non-null foreign key to `taxonomy_classification_jobs.id` with `ondelete="CASCADE"`.
- `next_job_id`: nullable foreign key to `taxonomy_classification_jobs.id` with `ondelete="SET NULL"`.
- `last_error`: nullable text.
- `created_at`: non-null timestamp with timezone.
- `updated_at`: non-null timestamp with timezone.
- Required constraints:
  - uniqueness over `(scope_node_id, node_id)`.
- Required indexes:
  - pending continuation lookup by `(updated_at, id)`.
- Write semantics:
  - accepted-result assignment movement inserts or updates one request for the moved card and target scope.
  - runtime drain deletes the request after successful next-job linkage or a valid no-op stop condition.
  - failed producer submission leaves the request retryable with `last_error` populated and `next_job_id` preserving the retry local job intent when one exists.

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
- Card current projection, formal version history, Workspace roles, unified proposals, and apply audits remain inside `knowledge_graph` table ownership.
- Taxonomy tree truth, current assignment truth, and taxonomy classification orchestration state remain outside `knowledge_graph` table ownership.
- Constraint and index naming follows shared SQLAlchemy metadata conventions unless fixed semantic names are explicitly required.

## Validation
- Metadata includes all accepted persistence models before migration autogeneration.
- Generated/applied schema enforces all required constraints and indexes.
- Generated/applied schema enforces taxonomy root uniqueness.
- Generated/applied schema enforces card version uniqueness, proposal type values, proposal status values, role values, and apply-audit references.
- Generated/applied schema allows later classification resubmission after a previous job for the same scope/card is locally processed or terminal.
- Vector type validity depends on PostgreSQL `vector` extension availability before dependent migration.
- Migration ordering/lifecycle checks are governed by `10-migration-lifecycle-governance`.
