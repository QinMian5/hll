---
abstract: Core data and domain model definition for V1 Node-Edge knowledge network, card versions, unified card proposals, reviewer apply audits, role-governed contribution, and adjacency-index read optimization.
out_of_scope: API endpoint contracts, SQL migration scripts, Figma UI designs, notification workflows, and large-scale partitioning strategy.
---

# Design: 02-core-domain-model

## Active Truth Policy
- This document defines only currently accepted V1 domain-model decisions.
- Superseded modeling choices are removed from active text.

## Context
- **Purpose:** Define the V1 persistent domain model for knowledge cards, card versions, unified human proposals, Knowledge-owned contribution roles, reviewer apply audits, and the read-optimized adjacency pattern.
- **Scope/Boundaries:** Covers `Node`, `CardVersion`, `CardProposal`, `WorkspaceRole`, `ProposalApplyAudit`, `Edge`, and `Adjacency` persistence semantics and read query shape.
- **Related Requirements:** R-002, R-004, R-005, R-006, R-008.

## Domain Model Definition

### Node
- `Node` is the atomic knowledge unit.
- `Node` owns the current card projection: title, content, current version, embedding, lifecycle state, and timestamps.
- `Node.current_version` is a positive integer and equals the highest formal card version for that node.
- Active nodes appear in ordinary Search and Graph View reads.
- Archived nodes are hidden from ordinary Search and Graph View reads by default.
- `Node.embedding` is required and uses fixed dimension `1536`.

### CardVersion
- `CardVersion` stores formal card history for audit, diff, review, and rollback baselines.
- `CardVersion.version` is a positive integer scoped to one `Node`.
- A card's first formal version is `1`.
- Formal updates create a new `CardVersion` and update the owning `Node` current projection in the same accepted apply operation.
- Pending proposals do not create card versions.

### WorkspaceRole
- `WorkspaceRole` stores Knowledge-owned contribution authorization keyed by Logto user id.
- Default signed-in users are contributors without requiring an explicit role row.
- Reviewer/admin grants are explicit Knowledge-owned records.
- Role records carry grant metadata and revoke metadata when the role is inactive.
- Logto remains the identity provider and does not own Workspace reviewer/admin governance.

### CardProposal
- `CardProposal` stores reviewable human-originated card maintenance requests.
- Proposal type is one of `create`, `edit`, or `delete`.
- Proposal status is one of `pending_review`, `accepted_applied`, `rejected`, or `withdrawn`.
- Common proposal fields include submitted user id, reason, reviewed user id, review note, created timestamp, updated timestamp, and reviewed timestamp.
- Type-specific payloads carry:
  - `create`: proposed title and proposed content.
  - `edit`: target node id, base version, suggested title, and suggested content.
  - `delete`: target node id, base version, target title, and target content from the referenced formal card version.
- Proposals that reference existing cards bind to formal card versions as review baselines.

### ProposalApplyAudit
- `ProposalApplyAudit` stores the outcome of reviewer acceptance.
- Each accepted-applied proposal has an independent apply audit record.
- The audit record identifies the proposal, reviewer, proposal type, affected nodes, created formal versions, archive outcomes when present, reviewer note, and apply timestamp.
- The audit record is written in the same accepted apply operation as the formal domain change and proposal status transition.

### Edge
- `Edge` is an undirected relation between two distinct nodes.
- V1 stores one canonical edge per unordered node pair.
- `Edge.strength` uses normalized range `[0, 1]`.
- V1 initialization selects edges from title-mention and semantic candidate pools.
- Title-mention candidates are existing active nodes whose normalized title appears as a complete normalized phrase in the new card content.
- Semantic candidates are selected by embedding similarity.
- Candidate budgets, semantic candidate pool size, and semantic strength threshold are runtime policy.
- V1 initialization rule for persisted strength is `strength = (dot_product + 1) / 2`.
- Edge initialization policy is not persisted as a transport field.

### Adjacency
- `Adjacency` is the physical read-optimization table for node-to-edge traversal.
- `Adjacency` does not change the canonical domain meaning of edges.
- Neighbor-query path is `Node -> Adjacency(node_id index) -> Edge`.

## Lifecycle And Apply Rules
- Reviewer acceptance is the only proposal transition that applies formal knowledge changes.
- `create` acceptance creates a new active `Node`, creates `CardVersion(version=1)`, and leaves taxonomy assignment to the standard direct `Root` assignment flow.
- `edit` acceptance creates a new `CardVersion` and updates the target node projection.
- `delete` acceptance marks the target node archived rather than physically deleting it.
- `rejected` and `withdrawn` proposals do not change formal card state.

## Read Model
- V1 graph read result model is `Subgraph`.
- `Subgraph` contains only:
  - `nodes`
  - `edges`
- Ordinary read models omit archived nodes by default.
- `Subgraph` excludes `edge_threshold`, `anchor`, and `stats`.

## Design Decisions

### Why This Design
- **Node + Edge as source of truth:** keeps domain semantics explicit and normalized.
- **CardVersion as formal card history:** gives proposals, audit, and rollback flows a stable card-content baseline without duplicating original content on every review surface.
- **Unified CardProposal:** keeps create, edit, and delete under one review queue and one lifecycle.
- **Knowledge-owned WorkspaceRole:** keeps contribution governance under product ownership while using Logto only for identity.
- **ProposalApplyAudit:** makes reviewer-applied outcomes independently auditable.
- **Adjacency as physical index table:** optimizes read-heavy neighbor queries without changing domain truth.
- **Canonical unordered edge pair:** prevents duplicate mirrored edges and enforces undirected semantics at storage level.

### Why Not Alternative Choices
- **Not creating separate review systems per proposal type:** duplicates lifecycle, permission, and audit rules.
- **Not physically deleting cards through reviewer apply:** weakens auditability and risks breaking historical references.
- **Not storing user name/email snapshots on proposal records:** user display data remains owned by Logto-backed identity lookup rather than duplicated inside card governance records.
- **Not using Logto roles as the Workspace authority:** reviewer certification is Knowledge product governance, not identity-provider tenancy.
- **Not introducing partitioning/sharding or other large-scale mechanisms in V1:** exceeds MVP complexity goals.

## Validation
- PostgreSQL extension `vector` is enabled before applying vector-backed schema.
- Neighbor-query path can be expressed as `Node -> Adjacency(node_id index) -> Edge`.
- Proposal diff path can be expressed from proposal payload to the referenced formal `CardVersion` baseline.
- Unordered-edge uniqueness and no-self-loop constraints are enforced by database constraints.
- Card version uniqueness, positive versions, proposal type values, proposal status values, and role values are enforced by database constraints or equivalent schema validation.
- Accepted proposal apply writes the formal domain change, final proposal status, and apply audit in one service operation.
- Ordinary Search and Graph View reads omit archived nodes by default.
- V1 documents only accepted current state and omits migration narration.
