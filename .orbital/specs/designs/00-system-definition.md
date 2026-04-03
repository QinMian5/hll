---
abstract: High-level system definition for an API-first open knowledge network.
out_of_scope: Implementation details, data-model internals, and module-level technical specifications.
---

# Design: 00-system-definition

## Active Truth Policy
- This document defines only the currently accepted system-definition decisions.
- Superseded boundaries are removed instead of described as transition history.

## System Definition
The system is an API-first open knowledge network for the agent era.
V1 exposes search read HTTP API requests and ingestion accept HTTP API requests as the external invocation channels.
The platform organizes knowledge as atomic cards and relation links to support machine-oriented retrieval and network visualization.

## Target Users
The primary target users are Agents.

## Core Value
The core value is to enable open knowledge dissemination and sharing in the agent era through a machine-consumable knowledge network.

## V1 Scope
### In Scope
- Search read HTTP API.
- Ingestion accept HTTP API for platform-official card construction.
- Search capability in V1 read APIs.
- Atomic knowledge cards.
- Relation links with dot-product-mapped strength computation in ingestion worker execution.
- 2D knowledge-card network visualization with zoom support.
- Platform-official knowledge construction.

### Out of Scope
- CLI product.
- User contribution workflow.
- Authentication, API keys, and token models.
- Source-verification requirements.
- Iterative relation-evolution algorithms beyond initial dot-product-based strength.

## Milestone Acceptance (V1)
- System baseline is established.
- Database baseline is established.
- Card-network visualization is available in the frontend.
- Ingestion-driven dot-product-mapped relation strength is computed and usable in search.

## Future Expansion Directions
- Community contribution and governance models.
- Authentication and access-control models.
- Source provenance and verification models.
- Relation-evolution algorithms beyond initial similarity.
