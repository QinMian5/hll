---
abstract: Versioned knowledge-card proposal design for card history, unified human proposals, reviewer apply outcomes, and Search/Workspace integration.
out_of_scope: Figma canvas construction, notification workflows, collaborative change-request threads, Logto tenant provisioning, and low-level SQL migration syntax.
---

# Design: knowledge-card-versioned-suggestions

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition history.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define how knowledge cards expose stable versions and accept role-governed human proposals through Search and Workspace.
- **Scope/Boundaries:** Covers card version semantics, unified proposal semantics, reviewer apply semantics, private API contract direction, web BFF auth/role enforcement, frontend Search/Workspace interactions, and validation expectations. Excludes Figma canvas construction, notification workflows, collaborative change-request threads, Logto operational setup, and detailed SQL migration syntax.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-006, R-007, R-008.

## Constraint Projection
- **Governing Constraints:** Knowledge-card proposals preserve an auditable relationship to the card versions visible to users, browser data access remains BFF-mediated, reviewer/admin authorization is Knowledge-owned, private API contracts remain generated and synchronized, and behavior-changing data-model/UI decisions stay reflected in active specs.
- **Detail Commitments:** Formal card content is versioned per node. Human-originated maintenance actions are represented as unified proposals with `create`, `edit`, and `delete` types. Proposals are submitted by authenticated users, reviewed by Knowledge-authorized reviewers, and applied immediately on acceptance. Search creates lightweight `create`, `edit`, and `delete` proposals. Workspace tracks the current user's submitted proposals through `My Proposals` only. Reviewer acceptance writes the formal domain change, final proposal state, and an independent apply audit record.
- **Update Rule:** Requirement-level governance remains stable while versioning, proposal persistence, endpoint contracts, and Search/Workspace UI behavior are maintained in this design document and related module projection documents.

## Inputs & Outputs
- **Inputs:**
  - Search result cards containing `node_id`, `current_version`, `title`, and `content`.
  - Search proposal forms for `create`, `edit`, and `delete`.
  - Authenticated web sessions resolved by the BFF from Logto-backed server-side session state.
  - Knowledge-owned reviewer/admin role grants.
  - Reviewer accept/reject decisions and reviewer notes.
- **Outputs:**
  - Formal card versions for accepted card content changes.
  - Pending, accepted-applied, rejected, or withdrawn proposal records.
  - Apply audit records for reviewer-accepted proposals.
  - Private API responses for Search, proposal creation, proposal listing, withdrawal, rejection, and accept/apply.
  - Browser-visible BFF responses for Search proposal submission and Workspace proposal workflows.
- **Artifacts:**
  - `apps/api/src/modules/knowledge_graph/`
  - `apps/api/src/modules/search/`
  - `apps/api/src/entrypoints/api/`
  - `apps/api/alembic/`
  - `apps/web/server/`
  - `apps/web/src/features/search/`
  - `apps/web/src/features/workspace/`
  - `packages/contracts/`

## Domain Model
- `nodes` holds the current active card projection:
  - `id`: integer primary key.
  - `title`: current card title.
  - `content`: current card content.
  - `current_version`: positive integer, per-card monotonic version.
  - lifecycle state sufficient to distinguish active and archived cards.
- `card_versions` holds formal card history:
  - `node_id`: owning card id.
  - `version`: positive integer, unique per card.
  - `title`: card title for that version.
  - `content`: card content for that version.
  - `created_at`: creation timestamp.
- `workspace_roles` holds Knowledge-owned contribution roles:
  - Logto user id.
  - role value for reviewer/admin authorization.
  - grant metadata.
  - revoke metadata when a role is no longer active.
- `card_proposals` holds unified human proposals:
  - proposal id.
  - proposal type: `create`, `edit`, or `delete`.
  - proposal status: `pending_review`, `accepted_applied`, `rejected`, or `withdrawn`.
  - submitted user id.
  - reviewed user id.
  - review note.
  - reason.
  - created, updated, and reviewed timestamps.
  - type-specific payload.
- `proposal_apply_audits` holds reviewer-acceptance outcomes:
  - proposal id.
  - reviewer user id.
  - proposal type.
  - affected node ids.
  - formal card versions created by the apply operation.
  - archive outcomes when present.
  - reviewer note.
  - apply timestamp.

## Version Semantics
- Card version numbers are scoped per card, not globally across all cards.
- A card's first formal version is `1`.
- `nodes.current_version` equals the highest formal `card_versions.version` for that card.
- Formal card updates assign `version = nodes.current_version + 1`, create one `card_versions` row, and update the `nodes` current projection in the same accepted apply operation.
- Pending proposals do not update `nodes` and do not create formal `card_versions` rows.
- Proposal baselines are read from formal card versions during diff, review, and audit.
- A proposal whose base version is lower than the card's current version remains reviewable when the referenced base version exists; review surfaces can identify that condition by comparing base version with current version.
- New accepted cards create initial formal version `1` in the same apply operation as the node.

## Proposal Semantics
- All `create`, `edit`, and `delete` proposals require a non-empty common `reason` explaining why the contributor recommends the proposed change.
- `create` proposal payload contains proposed title and proposed content.
- `edit` proposal payload contains target node id, base version, suggested title, and suggested content.
- `delete` proposal payload contains target node id, base version, target title, and target content read from the referenced formal card version.
- Contributors may withdraw only their own pending proposals.
- Reviewer rejection transitions a pending proposal to `rejected` and may include a review note.
- Reviewer acceptance transitions a pending proposal to `accepted_applied` only after the formal domain change and audit record are written.

## Apply Semantics
- `create` acceptance creates a formal card and its initial card version. The created card receives the standard direct `Root` taxonomy assignment and becomes Graph View visible after classification moves it into a browse-visible taxonomy card scope.
- `edit` acceptance creates a new formal version for the target card and updates the current projection.
- `delete` acceptance soft-archives the target card. Ordinary Search and Graph View results omit archived cards by default.
- Apply operations are backend-owned, permission-checked, and atomic at the service boundary.

## Private API Contract Direction
- `GET /api/v1/search?query=<string>` returns `matched_cards[]` items shaped with `node_id`, `current_version`, `title`, and `content`.
- Workspace proposal APIs provide private endpoints for:
  - creating proposals.
  - listing the current user's proposals.
  - listing pending proposals for reviewers.
  - withdrawing pending self-submitted proposals.
  - rejecting pending proposals.
  - accepting/applying pending proposals.
- Private proposal APIs receive the acting Logto user id through trusted BFF context rather than from browser-controlled payload fields.
- Proposal API contracts are part of the generated OpenAPI contract consumed by repository-owned web integration code.

## Web BFF Contract Direction
- Browser-side code calls BFF-owned `/web-api/*` routes for Search and Workspace proposal behavior.
- The BFF requires authenticated Logto-backed web sessions for proposal submission, withdrawal, review, and apply actions.
- The BFF derives the acting user id from the authenticated session.
- Browser requests must not provide user identity or role fields.
- Reviewer/admin actions require Knowledge-owned role authorization.
- Unauthenticated proposal requests return `401` with a web-safe error response.
- Unauthorized reviewer/admin requests return web-safe authorization errors.

## Frontend Interaction
- Search results render lightweight proposal affordances.
- Authenticated Search `Add card` activation opens the create mode of the Search Card Proposal Dialog.
- Authenticated Search edit activation opens the edit mode of the Search Card Proposal Dialog prefilled with the visible card title and content.
- Authenticated Search request-deletion activation opens the delete mode of the Search Card Proposal Dialog for the selected card.
- Anonymous Search proposal activation opens the sign-in-required dialog.
- Search proposal submission uses the unified proposal contracts.
- Search proposal submission requires a non-empty `Reason` field for add-card, edit-card, and delete-card modes.
- Search delete proposal submission stores the target card title and content from the referenced base version so Workspace proposal detail can render the proposed deletion's real card content from the proposal record.
- Search Card Proposal Dialog delete mode renders the selected card title and content through shared Input/Textarea `ReadOnly` states rather than disabled controls, preserving selectable content while distinguishing it from editable Reason input.
- Workspace does not expose contributor-facing create/edit/delete proposal forms.
- Workspace `My Proposals` shows the current user's proposal status.
- Workspace does not render `Review Queue` or `Role Management`.

## Validation
- **Checks:**
  - Persistence metadata supports formal card versions, Knowledge-owned roles, unified proposals, and apply audits.
  - Proposal status values are limited to `pending_review`, `accepted_applied`, `rejected`, and `withdrawn`.
  - Proposal type values are limited to `create`, `edit`, and `delete`.
  - Proposal reason is stored as a non-empty common field for create, edit, and delete proposals.
  - Search response contract includes `node_id` and `current_version` for every matched active card.
  - Search proposal creation stores the BFF-derived Logto user id and does not accept browser-supplied identity.
  - Workspace proposal creation rejects unauthenticated requests.
  - Reviewer accept/reject actions reject users without active reviewer/admin authorization.
  - Create acceptance creates a card and initial formal card version.
  - Edit acceptance creates a new formal card version.
  - Delete acceptance soft-archives the target card.
  - Apply acceptance writes an independent audit record.
  - Contract generation and drift checks cover changed Search and proposal API shapes.
  - Search delete proposal fields for the existing card use shared `ReadOnly` input and textarea state, not disabled state.
- **Evidence:**
  - Passing backend repository/service/API tests for card version and proposal persistence.
  - Passing BFF route and internal API adapter tests for proposal flows and role enforcement.
  - Passing frontend component/page tests for Search proposal interactions and Workspace current-user proposal tracking.
  - Visual inspection confirms the approved Figma Workspace and Search Card Proposal Dialog frames.
