---
abstract: Versioned knowledge-card suggestion design for card history, user-submitted edit suggestions, authenticated submission, and Search UI integration.
out_of_scope: Review-workbench UI, card-merge conflict resolution, multi-branch version graphs, and Logto tenant provisioning.
---

# Design: knowledge-card-versioned-suggestions

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition history.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define how knowledge cards expose stable versions and accept authenticated user edit suggestions from the Search experience.
- **Scope/Boundaries:** Covers card version semantics, suggested-edit persistence, private API contracts, web BFF auth enforcement, frontend Search interactions, and validation expectations. Excludes review-workbench UI, acceptance/rejection UI, automated merge logic, and Logto operational setup.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Knowledge-card edit suggestions must preserve an auditable relationship to the card version seen by the user, browser data access must remain BFF-mediated, private API contracts must remain generated and synchronized, and behavior-changing data-model/UI decisions must stay reflected in active specs.
- **Detail Commitments:** Each persisted knowledge card has an integer `current_version`. Each formal card version is represented by a `card_versions` row keyed by `node_id` plus integer `version`. User suggestions are represented by `card_suggested_edits` rows that bind the suggestion to a `node_id` and `base_version`, store only the proposed `title` and `content`, store the authenticated Logto user id as `suggested_by_user_id`, and carry `pending`, `accepted`, or `rejected` status. Browser clients receive `node_id` and `current_version` from Search results, return `base_version` with the suggestion payload, and never submit `suggested_by_user_id`; the BFF derives that user id from the server-side session and forwards it through the trusted internal API context.
- **Update Rule:** Requirement-level governance remains stable while versioning, suggestion persistence, endpoint contracts, and Search UI behavior are maintained in this design document and the related module projection documents.

## Inputs & Outputs
- **Inputs:**
  - Search result cards containing `node_id`, `current_version`, `title`, and `content`.
  - Authenticated web sessions resolved by the BFF from Logto-backed server-side session state.
  - User-submitted suggested `title` and `content` values from the Search card suggestion dialog.
  - Figma Search suggestion and sign-in-required dialog frames in file `WBYs6P9HMxe21TSYQL637r`.
- **Outputs:**
  - Versioned card-history rows for every formal card version.
  - Pending suggested-edit rows tied to the version seen by the user.
  - Private API responses for Search and suggested-edit creation.
  - Browser-visible BFF responses for authenticated suggestion creation and unauthenticated sign-in prompts.
- **Artifacts:**
  - `apps/api/src/modules/knowledge_graph/`
  - `apps/api/src/modules/search/`
  - `apps/api/src/entrypoints/api/`
  - `apps/api/alembic/`
  - `apps/web/server/`
  - `apps/web/src/features/search/`
  - `packages/contracts/`

## Domain Model
- `nodes` holds the current card projection:
  - `id`: SQLAlchemy default integer primary key.
  - `title`: current card title.
  - `content`: current card content.
  - `current_version`: integer, non-null, per-card monotonic version, minimum `1`.
- `card_versions` holds formal card history:
  - `id`: SQLAlchemy default integer primary key.
  - `node_id`: owning card id.
  - `version`: integer, non-null, per-card monotonic version, minimum `1`.
  - `title`: card title for that version.
  - `content`: card content for that version.
  - `created_at`: creation timestamp.
  - Required uniqueness: `(node_id, version)`.
- `card_suggested_edits` holds user suggestions:
  - `id`: SQLAlchemy default integer primary key.
  - `node_id`: target card id.
  - `base_version`: integer card version the user saw when preparing the suggestion.
  - `suggested_title`: proposed card title.
  - `suggested_content`: proposed card content.
  - `suggested_by_user_id`: authenticated Logto user id string.
  - `status`: `pending`, `accepted`, or `rejected`, default `pending`.
  - `created_at`: creation timestamp.
  - `updated_at`: update timestamp.
  - Required reference: `(node_id, base_version)` references `card_versions(node_id, version)`.

## Version Semantics
- Card version numbers are scoped per card, not globally across all cards.
- A card's first formal version is `1`.
- `nodes.current_version` equals the highest formal `card_versions.version` for that card.
- Formal card updates assign `version = nodes.current_version + 1`, create one `card_versions` row, and update the `nodes` current projection in the same transaction.
- Suggested edits do not update `nodes` and do not create formal `card_versions` rows while they are pending.
- Suggested edits store proposed `title` and `content` only. The original baseline content is read from `card_versions(node_id, base_version)` when diffing, reviewing, or auditing the suggestion.
- A suggestion whose `base_version` is lower than the card's `current_version` remains valid when the referenced base version exists. Review surfaces can identify that condition by comparing `base_version` with `current_version`.
- Before suggestion submission is enabled for existing data, every existing `nodes` row must have `current_version = 1` and a corresponding `card_versions(version = 1)` row with the same `title` and `content`. New ingested nodes create that initial formal version in the same unit of work as the node.

## Private API Contract
- `GET /api/v1/search?query=<string>` returns `matched_cards[]` items shaped as:
  - `node_id`
  - `current_version`
  - `title`
  - `content`
- `POST /api/v1/cards/{node_id}/suggested-edits` creates a pending suggestion.
- Suggested-edit request body:
  - `base_version`
  - `suggested_title`
  - `suggested_content`
- Suggested-edit trusted internal context:
  - authenticated Logto user id forwarded by the BFF as the suggestion principal.
- Suggested-edit response body:
  - `id`
  - `node_id`
  - `base_version`
  - `status`
  - `created_at`
- Private API validation:
  - target card exists.
  - `(node_id, base_version)` exists in `card_versions`.
  - `suggested_title` and `suggested_content` are non-empty after validation trimming rules.
  - suggestion values differ from the referenced base version.
  - status for creation is `pending`.

## Web BFF Contract
- Browser-side code calls `POST /web-api/cards/{node_id}/suggested-edits` for suggestion creation.
- The BFF requires an authenticated Logto-backed web session for suggestion creation.
- The BFF derives `suggested_by_user_id` from the authenticated session user id.
- Browser requests must not provide `suggested_by_user_id`.
- Unauthenticated suggestion requests return `401` with a web-safe error response.
- Authenticated suggestion requests are forwarded to private `POST /api/v1/cards/{node_id}/suggested-edits` through the generated internal API client with the BFF-derived user id in trusted internal context.
- Search data continues to flow through `GET /web-api/search`, which maps to private `GET /api/v1/search`.

## Frontend Search Interaction
- Search result cards render an edit icon button aligned with the approved Figma Search frames.
- When the current browser session is authenticated, activating the edit button opens the `Suggest edit` dialog.
- The suggestion dialog is prefilled with the card title and content the user sees.
- The suggestion form holds the card's `node_id` and `current_version` from the Search result as its submission target and `base_version`.
- Submission payload contains `base_version`, `suggested_title`, and `suggested_content`.
- Submission payload does not contain user identity fields.
- The submit action is disabled when title and content match the visible card values.
- Submission success closes the suggestion dialog.
- Submission failure is displayed inside the dialog without clearing the user's draft.
- When the current browser session is anonymous, activating the edit button opens the sign-in-required dialog instead of the suggestion form.
- The sign-in-required dialog follows Figma file `WBYs6P9HMxe21TSYQL637r`:
  - desktop frame `561:453`.
  - mobile frame `561:610`.
  - title `Sign in to suggest edits`.
  - body `Sign in to suggest changes and help improve this knowledge card.`
  - primary action `Sign in`.
  - close button and scrim dismissal behavior.
- The sign-in action starts the BFF-owned Logto sign-in flow.

## Validation
- **Checks:**
  - Persistence metadata includes `nodes.current_version`, `card_versions`, and `card_suggested_edits`.
  - Database constraints enforce positive integer versions, unique `(node_id, version)`, valid suggestion status values, and suggestion base-version references.
  - Search response contract includes `node_id` and `current_version` for every matched card.
  - Suggested-edit creation stores the BFF-derived Logto user id and does not accept browser-supplied user identity.
  - Suggested-edit creation rejects unknown cards, unknown base versions, empty proposed values, and no-op proposed values.
  - Suggested-edit creation accepts a stale but existing `base_version`.
  - BFF tests cover authenticated forwarding and unauthenticated `401` behavior.
  - Frontend tests cover authenticated suggestion dialog opening, anonymous sign-in-required dialog opening, no-op submit disabling, and submission payload shape.
  - Contract generation and drift checks cover the changed Search and suggested-edit API shapes.
- **Evidence:**
  - Passing backend repository/service/API tests for card version and suggestion persistence.
  - Passing BFF route and internal API adapter tests.
  - Passing frontend component/page tests for Search edit interactions.
  - Visual inspection confirms the sign-in-required dialog matches the approved Figma desktop and mobile frames.
