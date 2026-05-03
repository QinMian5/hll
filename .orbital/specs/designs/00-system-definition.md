---
abstract: High-level system definition for a public web, public MCP, private API, and operator-assisted open knowledge network.
out_of_scope: Implementation details, data-model internals, and module-level technical specifications.
---

# Design: 00-system-definition

## Active Truth Policy
- This document defines only currently accepted system-definition decisions.
- Superseded boundaries are removed instead of preserved as transition history.

## System Definition
The system is an open knowledge network for the agent era with public web and MCP access surfaces, private service APIs, role-governed human contribution, and operator-assisted source processing.
V1 exposes public web browsing and search through a BFF, a role-governed web Workspace for human card proposals and reviewer apply flows, public MCP search through a Logto personal-access-token boundary, private internal search read, taxonomy drill-down read, and ingestion accept HTTP APIs, plus a local operator-facing CLI for reviewed card submission.
The platform organizes knowledge as atomic cards and relation links to support machine-oriented retrieval, taxonomy-first hierarchical exploration, role-governed human maintenance, and operator-guided incremental classification.

## Target Users
The primary target users are Agents.
Human contributors, reviewers, and operators maintain knowledge quality through role-governed web and operator surfaces.

## Core Value
The core value is open knowledge dissemination through a machine-consumable knowledge graph with authoritative taxonomy classification.

## V1 Scope
### In Scope
- Private internal search read HTTP API.
- Private internal taxonomy drill-down HTTP APIs for root, id-addressed nodes, canonical LCC path-addressed nodes, and leaf viewport data.
- Public web access through a BFF with anonymous browsing quotas and Logto-backed sign-in for higher quotas.
- Role-governed web Workspace for human card proposals, proposal tracking, reviewer accept/apply, reviewer rejection, and admin role-management placement.
- Public MCP search access through Logto personal-access-token authentication, account-level quota, and token-level attribution.
- Private internal ingestion accept HTTP API for platform-official card construction.
- Local operator-facing CLI for single-card review and submission into ingestion API.
- Atomic knowledge cards.
- Relation links with dot-product-mapped strength computation in ingestion worker execution.
- Taxonomy-backed hierarchical browsing with branch/leaf query responses.
- Operator-managed taxonomy structure with visible virtual `Unclassified` card scopes over direct assignments.
- Background taxonomy classification through `job-queue-mcp`.
- Leaf-level one-hop graph view (inner + pulled outer nodes, scoped edges).
- Backend-owned taxonomy view read models provide branch and leaf browsing data, including backend-computed leaf coordinates.

### Out of Scope
- Semantic-map snapshot rebuild and tile browsing.
- Multi-card or interactive authoring CLI workflows beyond single-card review/submission.
- Public REST API access for external users or external programmatic clients.
- Source-verification requirements.
- Iterative relation-evolution algorithms beyond initial dot-product strength.

## Milestone Acceptance (V1)
- System baseline is established.
- Database baseline is established.
- Taxonomy drill-down visualization is available in frontend.
- Public web browsing works through the BFF access boundary with anonymous and logged-in quota policy.
- Human card maintenance works through the role-governed Workspace proposal and reviewer apply boundary.
- Public MCP search works through the MCP access boundary with Logto personal-access-token authentication and usage attribution.
- Ingestion-driven relation strength is computed and usable in search and leaf-level graph views.
- New cards enter taxonomy browsing as direct `Root` assignments exposed through the root `Unclassified` card scope.
- Background classification can iteratively move cards from visible `Unclassified` card scopes into accepted taxonomy target scopes.
