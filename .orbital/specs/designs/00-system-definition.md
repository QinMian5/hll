---
abstract: High-level system definition for an API-first and operator-assisted open knowledge network.
out_of_scope: Implementation details, data-model internals, and module-level technical specifications.
---

# Design: 00-system-definition

## Active Truth Policy
- This document defines only currently accepted system-definition decisions.
- Superseded boundaries are removed instead of preserved as transition history.

## System Definition
The system is an API-first open knowledge network for the agent era.
V1 exposes search read, taxonomy drill-down read, and ingestion accept HTTP APIs, plus a local operator-facing CLI for reviewed card submission.
The platform organizes knowledge as atomic cards and relation links to support machine-oriented retrieval, taxonomy-first hierarchical exploration, and operator-guided incremental classification.

## Target Users
The primary target users are Agents.

## Core Value
The core value is open knowledge dissemination through a machine-consumable knowledge graph with authoritative taxonomy classification.

## V1 Scope
### In Scope
- Search read HTTP API.
- Taxonomy drill-down HTTP APIs (`/api/v1/taxonomy/view/root`, `/api/v1/taxonomy/view/nodes/{node_id}`).
- Ingestion accept HTTP API for platform-official card construction.
- Local operator-facing CLI for single-card review and submission into ingestion API.
- Atomic knowledge cards.
- Relation links with dot-product-mapped strength computation in ingestion worker execution.
- Taxonomy-backed hierarchical browsing with branch/leaf query responses.
- Operator-managed taxonomy structure with visible `Unclassified` leaves.
- Background taxonomy classification through `job-queue-mcp`.
- Leaf-level one-hop graph view (inner + pulled outer nodes, scoped edges).
- Frontend-owned graph layout (backend does not return authoritative node coordinates).

### Out of Scope
- Semantic-map snapshot rebuild and tile browsing.
- Multi-card or interactive authoring CLI workflows beyond single-card review/submission.
- User contribution workflow.
- Authentication, API keys, and token models.
- Source-verification requirements.
- Iterative relation-evolution algorithms beyond initial dot-product strength.

## Milestone Acceptance (V1)
- System baseline is established.
- Database baseline is established.
- Taxonomy drill-down visualization is available in frontend.
- Ingestion-driven relation strength is computed and usable in search and leaf-level graph views.
- New cards enter taxonomy browsing through `Root -> Unclassified`.
- Background classification can move cards from a scope's `Unclassified` leaf into child-scope `Unclassified` leaves.

## Future Expansion Directions
- Community contribution and governance models.
- Authentication and access-control models.
- Source provenance and verification models.
- Relation-evolution algorithms beyond initial similarity.
