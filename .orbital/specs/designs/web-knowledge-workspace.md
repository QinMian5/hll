---
abstract: Role-governed web Workspace design for human knowledge-card proposals, reviewer apply flows, proposal tracking, and admin role boundaries.
out_of_scope: Figma canvas construction, implementation plan steps, notification workflows, collaborative change-request threads, billing, and Logto tenant administration.
---

# Design: web-knowledge-workspace

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the web Workspace product surface and supporting domain behavior for role-governed human maintenance of the knowledge graph.
- **Scope/Boundaries:** Covers Workspace information architecture, Knowledge-owned contribution roles, unified proposal types, proposal lifecycle states, reviewer accept/apply semantics, audit expectations, Search proposal integration, and first-version phasing. Excludes Figma drawing execution, detailed implementation planning, notification systems, comment threads, billing, and Logto operational setup.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-006, R-007, R-008.

## Constraint Projection
- **Governing Constraints:** Human-originated knowledge changes remain role-governed, reviewable, and auditable. Public browser access remains BFF-mediated. Internal API access remains contract-driven through generated artifacts. Active specs stay synchronized with accepted behavior.
- **Detail Commitments:** The web client exposes `Workspace` as an authenticated account-menu route inside the existing app shell. Search owns lightweight proposal entry for adding cards, editing cards, and requesting card deletion. Workspace owns proposal tracking, reviewer queue access, and admin role-management placement. Search-submitted records use the same unified proposal model that Workspace tracks and reviewers apply. Reviewer acceptance applies the formal knowledge-graph change immediately and writes an independent audit record. Knowledge owns reviewer/admin authorization using Logto user ids as identity keys; Logto remains the identity provider rather than the contribution-role store.
- **Update Rule:** Requirement-level role-governance constraints remain stable in `requirements.md`; Workspace route structure, proposal behavior, role ownership, and apply/audit semantics stay in this design document and related web/BFF/domain design documents.

## Product Model
- **Contributor:** A signed-in user without explicit reviewer/admin grant. Contributors can submit proposals and withdraw their own pending proposals.
- **Reviewer:** A Knowledge-authorized user who can review pending proposals and accept/apply or reject them.
- **Admin:** A Knowledge-authorized user who can manage reviewer authorization. The first implementation phase may rely on operator-managed role seeding while the product design preserves the admin role-management surface.
- **Anonymous user:** A user without a signed-in web session. Anonymous users can browse permitted public surfaces but cannot submit, review, withdraw, or administer proposals.

## Workspace Information Architecture
- `Workspace` is reached from the authenticated account menu between `Dashboard` and `Settings`.
- The Workspace route contains three product views:
  - `My Proposals`: contributor-facing status tracking for proposals submitted by the current user.
  - `Review Queue`: reviewer/admin-facing pending proposal review and accept/reject actions.
  - `Role Management`: admin-facing reviewer authorization management. First-phase implementation may defer this view while keeping the route and permission boundary explicit in design.
- Ordinary contributors see `My Proposals`.
- Reviewers see `My Proposals` plus `Review Queue`.
- Admins see contributor views, `Review Queue`, and `Role Management`.

## Unified Proposal Model
- The system uses one proposal model for all human-originated card maintenance actions.
- Proposal types are `create`, `edit`, and `delete`.
- Proposal statuses are `pending_review`, `accepted_applied`, `rejected`, and `withdrawn`.
- Common proposal fields include proposal id, proposal type, status, submitted user id, reviewed user id, review note, created timestamp, updated timestamp, and reviewed timestamp.
- Type-specific payloads:
  - `create`: proposed title and proposed content.
  - `edit`: target node id, base version, suggested title, and suggested content.
  - `delete`: target node id, base version, and reason.

## Proposal Semantics
- `create` acceptance creates a formal card and its initial version. The accepted card enters taxonomy browsing through the existing default assignment rule: direct `Root` assignment exposed as visible `Unclassified` until classification moves it.
- `edit` acceptance creates a new formal card version for the target card and updates the current card projection.
- `delete` acceptance performs soft archive rather than physical deletion. Archived cards are hidden from ordinary Search and Graph View results by default while versions, proposals, audit records, and maintenance visibility remain available.
- `rejected` proposals carry a reviewer note when useful.
- `withdrawn` is available only to the submitting contributor while a proposal is still pending review.

## Reviewer Apply And Audit
- Reviewer acceptance applies the proposal immediately.
- The apply operation is backend-owned and must be permission-checked server-side.
- The apply operation writes the formal knowledge-graph domain change, the final proposal status, and an independent apply audit record.
- The audit record identifies the proposal id, reviewer user id, proposal type, affected node ids, formal versions created by the apply operation, archive outcomes when present, reviewer note, and apply timestamp.
- Apply behavior is atomic at the service boundary: the formal domain change, proposal transition, and audit record converge as one accepted outcome.

## Search Integration
- Search remains a discovery and lightweight contribution page.
- Search Results expose `Add Card` in the results header and edit affordances on result cards.
- The Search Card Proposal Dialog exposes create, edit, and request-deletion modes.
- Search-submitted proposals use the same unified proposal model tracked by Workspace.
- Workspace does not expose contributor-facing create/edit/delete proposal forms.
- A proposal submitted from Search appears in `My Proposals` and is reviewed through the same `Review Queue` as every other pending proposal.

## Access Boundary And Data Flow
- Browser code calls only BFF-owned `/web-api/*` endpoints for Workspace behavior.
- The BFF resolves the Logto-backed web session and uses the authenticated user id as the principal.
- Knowledge-owned roles determine which Workspace views and actions are allowed.
- Role and action authorization is enforced server-side. Frontend visibility is a convenience, not the security boundary.
- The BFF calls private FastAPI endpoints through generated internal API contracts.
- FastAPI owns proposal persistence, role persistence, proposal state transitions, apply services, and audit writes.
- Frontend code consumes generated contract artifacts rather than handwritten backend schemas.

## First-Version Phasing
- Phase 1 covers Knowledge-owned roles, Search create proposals, Search edit proposals, Search delete proposals, `My Proposals`, `Review Queue`, accept/apply, reject, withdraw, audit records, and Search integration with the unified proposal model.
- Phase 2 covers the admin Role Management UI. Operator-managed reviewer/admin seeding is acceptable before the Role Management UI is implemented.

## Figma-First UI Projection
- Workspace UI is designed in Figma before frontend code implementation.
- Figma coverage includes desktop and mobile frames for Workspace inside the existing app shell, `My Proposals`, `Review Queue`, `Role Management`, and Search lightweight entry into the unified proposal model.
- Workspace is a working product surface, not a landing page.
- Workspace page headers use the shared routed-page header tokens defined by the app shell: `layout/page/header-height`, `typography/page/title/font-size`, `typography/page/title/line-height`, `typography/page/subtitle/font-size`, `typography/page/subtitle/line-height`, and `layout/page/header-title-gap`.
- The `My Proposals` Workspace header does not render a top-right `Contributor` role badge. Contributor access is implied by the current view and server-side permissions, while reviewer/admin-specific indicators remain scoped to privileged views where they add decision value.
- Visual language follows the existing app shell, Search, Dashboard, Docs, and Settings style: restrained, business-like, high-frequency maintenance oriented, and aligned with existing Tailwind/shadcn-style primitives.

## Validation
- **Checks:**
  - `Workspace` appears as an authenticated account-menu item between `Dashboard` and `Settings`.
  - Anonymous users cannot submit, withdraw, review, apply, reject, or administer proposals.
  - Signed-in contributors can submit proposals and view their own proposals.
  - Contributors can withdraw their own pending proposals and cannot withdraw reviewed proposals.
  - Reviewers can access pending proposals in `Review Queue`.
  - Reviewers can reject pending proposals with reviewer notes.
  - Reviewer acceptance applies the formal domain change and transitions the proposal to `accepted_applied`.
  - Reviewer acceptance writes an independent audit record.
  - Create acceptance creates a formal card and uses the existing Root/Unclassified taxonomy default.
  - Edit acceptance creates a new formal card version for the target card.
  - Delete acceptance soft-archives the target card and ordinary Search/Graph View reads omit archived cards by default.
  - Search edit submission creates the unified `edit` proposal type.
  - Search create submission creates the unified `create` proposal type.
  - Search delete submission creates the unified `delete` proposal type.
  - Workspace desktop and mobile page headers use the shared routed-page header height, title typography, subtitle typography, and title-gap tokens.
  - Workspace `My Proposals` desktop and mobile headers do not show a top-right `Contributor` role badge.
  - Frontend Workspace API integration consumes generated contracts rather than handwritten backend schemas.
- **Evidence:**
  - Active specs describe one proposal model and one review/apply path for human-originated card maintenance.
  - Figma frames capture the accepted Workspace page structure before frontend implementation begins.
  - Future implementation verification covers backend proposal services, BFF role enforcement, frontend route visibility, and Search-to-proposal integration.
