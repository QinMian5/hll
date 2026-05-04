---
abstract: Web Workspace design for current-user human knowledge-card proposal tracking and Search proposal integration.
out_of_scope: Figma canvas construction, implementation plan steps, notification workflows, collaborative change-request threads, reviewer queue UI, role-management UI, billing, and Logto tenant administration.
---

# Design: web-knowledge-workspace

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the web Workspace product surface for current-user tracking of role-governed human maintenance proposals.
- **Scope/Boundaries:** Covers Workspace information architecture, Knowledge-owned contribution roles, unified proposal types, proposal lifecycle states, reviewer accept/apply semantics, audit expectations, Search proposal integration, and first-version phasing. Excludes Figma drawing execution, detailed implementation planning, notification systems, comment threads, reviewer queue UI, role-management UI, billing, and Logto operational setup.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-006, R-007, R-008.

## Constraint Projection
- **Governing Constraints:** Human-originated knowledge changes remain role-governed, reviewable, and auditable. Public browser access remains BFF-mediated. Internal API access remains contract-driven through generated artifacts. Active specs stay synchronized with accepted behavior.
- **Detail Commitments:** The web client exposes `Workspace` as an authenticated account-menu route inside the existing app shell. Search owns lightweight proposal entry for adding cards, editing cards, and requesting card deletion. Workspace owns current-user proposal tracking through `My Proposals` only. Workspace does not expose contributor-facing create/edit/delete forms, `Review Queue`, or `Role Management`. Search-submitted records use the same unified proposal model that Workspace tracks and reviewers apply through role-governed service flows outside the Workspace route. Reviewer acceptance applies the formal knowledge-graph change immediately and writes an independent audit record. Knowledge owns reviewer/admin authorization using Logto user ids as identity keys; Logto remains the identity provider rather than the contribution-role store.
- **Update Rule:** Requirement-level role-governance constraints remain stable in `requirements.md`; Workspace route structure, proposal behavior, role ownership, and apply/audit semantics stay in this design document and related web/BFF/domain design documents.

## Product Model
- **Contributor:** A signed-in user without explicit reviewer/admin grant. Contributors can submit proposals and withdraw their own pending proposals.
- **Reviewer:** A Knowledge-authorized user who can review pending proposals and accept/apply or reject them through role-governed service flows outside the Workspace route.
- **Admin:** A Knowledge-authorized user who can manage reviewer authorization outside the current Workspace route. The first implementation phase may rely on operator-managed role seeding.
- **Anonymous user:** A user without a signed-in web session. Anonymous users can browse permitted public surfaces but cannot submit, review, withdraw, or administer proposals.

## Workspace Information Architecture
- `Workspace` is reached from the authenticated account menu between `Dashboard` and `Settings`.
- The Workspace route contains one product view:
  - `My Proposals`: status tracking for proposals submitted by the current signed-in user.
- Ordinary contributors, reviewers, and admins see the same Workspace route shape: `My Proposals` only.
- Workspace does not render view tabs when only `My Proposals` exists.

## Unified Proposal Model
- The system uses one proposal model for all human-originated card maintenance actions.
- Proposal types are `create`, `edit`, and `delete`.
- Proposal statuses are `pending_review`, `accepted_applied`, `rejected`, and `withdrawn`.
- Common proposal fields include proposal id, proposal type, status, submitted user id, reason, reviewed user id, review note, created timestamp, updated timestamp, and reviewed timestamp.
- Type-specific payloads:
  - `create`: proposed title and proposed content.
  - `edit`: target node id, base version, suggested title, and suggested content.
  - `delete`: target node id and base version.

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
- The Search Card Proposal Dialog labels the contributor explanation field `Reason` and requires it for create, edit, and request-deletion modes.
- Search-submitted proposals use the same unified proposal model tracked by Workspace.
- Workspace does not expose contributor-facing create/edit/delete proposal forms.
- A proposal submitted from Search appears in `My Proposals` and is reviewed through role-governed service flows outside the Workspace route.

## Access Boundary And Data Flow
- Browser code calls only BFF-owned `/web-api/*` endpoints for Workspace behavior.
- The BFF resolves the Logto-backed web session and uses the authenticated user id as the principal.
- Workspace frontend behavior requests only the current user's proposal list.
- Knowledge-owned roles determine which review, apply, and administration actions are allowed outside the current Workspace route.
- Role and action authorization is enforced server-side.
- The BFF calls private FastAPI endpoints through generated internal API contracts.
- FastAPI owns proposal persistence, role persistence, proposal state transitions, apply services, and audit writes.
- Frontend code consumes generated contract artifacts rather than handwritten backend schemas.

## First-Version Phasing
- Phase 1 covers Knowledge-owned roles, Search create proposals, Search edit proposals, Search delete proposals, `My Proposals`, accept/apply service behavior, reject service behavior, withdraw service behavior, audit records, and Search integration with the unified proposal model.
- Role-management UI is outside the current Workspace route. Operator-managed reviewer/admin seeding is acceptable while no role-management product surface exists.

## Figma-First UI Projection
- Workspace UI is designed in Figma before frontend code implementation.
- Figma coverage includes desktop and mobile frames for Workspace inside the existing app shell, `My Proposals`, and Search lightweight entry into the unified proposal model.
- Workspace is a working product surface, not a landing page.
- Workspace page headers use the shared routed-page header tokens defined by the app shell: `layout/page/header-height`, `typography/page/title/font-size`, `typography/page/title/line-height`, `typography/page/subtitle/font-size`, `typography/page/subtitle/line-height`, and `layout/page/header-title-gap`.
- The `My Proposals` Workspace header does not render a top-right `Contributor` role badge. Contributor access is implied by the current view and server-side permissions.
- When the current user has no proposals, the Workspace split view keeps the same `Proposals` rail and `Proposal Detail` panel structure. The rail renders the centered `No Proposals Yet` empty state, and the detail panel renders the centered `No Proposal Selected` empty state. Empty states do not render subtitles, add icons, or contributor actions.
- Proposal detail fields use shared Input/Textarea components in the `ReadOnly` state rather than `Disabled`, so submitted proposal content remains selectable and copyable while visually distinct from editable form fields.
- The populated proposal detail panel uses a fixed bottom action bar. The action bar contains a secondary `Cancel Proposal` button with the shared Lucide `X` icon. The button is enabled only for the submitter's own `pending_review` proposals and calls the Workspace withdrawal flow; reviewed or withdrawn proposals render the same control in a disabled state.
- Visual language follows the existing app shell, Search, Dashboard, Docs, and Settings style: restrained, business-like, high-frequency maintenance oriented, and aligned with existing Tailwind/shadcn-style primitives.

## Validation
- **Checks:**
  - `Workspace` appears as an authenticated account-menu item between `Dashboard` and `Settings`.
  - Anonymous users cannot submit, withdraw, review, apply, reject, or administer proposals.
  - Signed-in contributors can submit proposals and view their own proposals.
  - Contributors can withdraw their own pending proposals and cannot withdraw reviewed proposals.
  - Workspace does not render `Review Queue` or `Role Management`.
  - Workspace does not render view tabs while `My Proposals` is the only Workspace view.
  - Reviewers can reject pending proposals with reviewer notes through role-governed service flows outside the Workspace route.
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
  - Workspace with no current-user proposals renders the Figma-approved `No Proposals Yet` rail empty state and vertically centered `No Proposal Selected` detail-panel empty state without subtitles or add icons.
  - Workspace proposal detail fields render with shared `ReadOnly` input and textarea state, not disabled state.
  - Workspace populated proposal details render a fixed bottom action bar with a secondary `Cancel Proposal` button using the shared Lucide `X` icon.
  - Workspace cancellation is enabled only for current-user `pending_review` proposals and uses the BFF-mediated withdrawal endpoint.
  - Frontend Workspace API integration consumes generated contracts rather than handwritten backend schemas.
- **Evidence:**
  - Active specs describe one proposal model and one review/apply path for human-originated card maintenance.
  - Figma frames capture the accepted Workspace page structure before frontend implementation begins.
  - Future implementation verification covers backend proposal services, BFF role enforcement, Workspace current-user proposal tracking, and Search-to-proposal integration.
