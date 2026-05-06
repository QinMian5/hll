---
abstract: Web account settings design for updating the authenticated user's Logto profile name through the BFF.
out_of_scope: Logto tenant provisioning, password and email flows, Knowledge-owned user-profile persistence, and non-account preferences.
---

# Design: web-account-settings

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the Settings page workflow for authenticated browser users to view and update their account display name.
- **Scope/Boundaries:** Covers `/settings` page layout, one `Name` field, autosave interaction, BFF profile endpoint behavior, Logto Account API integration, session/profile consistency, and validation expectations. Excludes password, email, avatar, username, custom data, application preferences, Knowledge-owned profile storage, and shared web auth/session orchestration.
- **Related Requirements:** R-001, R-003, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Browser-visible account settings must use the public web BFF boundary, must keep Logto as the account profile authority, must follow the shared web auth/session boundary, must keep browser tokens out of frontend runtime state, and must keep settings UI behavior synchronized with active specs.
- **Detail Commitments:** The Settings route follows Figma file `WBYs6P9HMxe21TSYQL637r`, Settings canvas node `474:84`, desktop frame `476:42`, and mobile frame `476:79`. The settings surface contains only the `Name` field. The browser calls same-origin `/web-api/*` endpoints only. The BFF uses the authenticated server-side Logto session to fetch and patch Logto Account API profile data. Knowledge does not persist a separate account profile table.
- **Update Rule:** Project requirements remain stable while `/settings` layout, web profile endpoint shape, Logto Account API adapter behavior, and autosave rules stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Browser route navigation to `/settings`.
  - BFF-owned web session cookie.
  - Current authenticated Logto account profile.
  - User edits to the `Name` input.
  - Logto Account API responses from `GET /api/my-account` and `PATCH /api/my-account`.
- **Outputs:**
  - Settings page content rendered inside the shared app shell.
  - Browser-safe account profile data containing user `id`, optional `email`, and optional `name`.
  - Profile update responses that reflect the saved Logto `name`.
  - Field-local invalid styling plus content-area notification state when validation, authentication, or Logto update fails.
- **Artifacts:**
  - `apps/web/server/auth/logto.ts`
  - `apps/web/server/auth/routes.ts`
  - `apps/web/server/auth/sessionState.ts`
  - `apps/web/server/auth/routes.test.ts`
  - `apps/web/src/shared/web-api/session.ts`
  - `apps/web/src/shared/web-api/sessionQueries.ts`
  - `apps/web/src/features/settings/pages/index.tsx`
  - Settings feature-local frontend helpers or tests under `apps/web/src/features/settings/` as needed.

## Design Approach
- **Approach:** The Settings page is an authenticated account page inside the existing shared app shell. It reads browser-safe account profile data through the BFF, renders the Figma-aligned `Name` form, and saves the trimmed name on blur or Enter. The BFF keeps Logto as the source of account profile truth by calling the Logto Account API with server-side session credentials.
- **Key Elements:**
  - **Route ownership:** `/settings` remains an account-menu route and is not added to the primary sidebar navigation.
  - **Authenticated boundary:** Authenticated users see the Settings content. Anonymous or expired-session direct visits use the shared web auth coordinator to start interactive sign-in with `/settings` as the `return_to` value. The Settings page does not own a page-local anonymous sign-in prompt as its primary access behavior.
  - **Figma projection:** Desktop uses the `1120px` main region with `32px` content padding, a `720px` Settings column, a title-only page header, and a quiet `720px x 72px` settings-list panel placed `24px` below the title. The page header uses the shared routed-page header height token and is `48px` tall on desktop and mobile. The normal default state does not render an `Account` header, section header, subtitle, helper, metadata, separator, or saved-status copy. The desktop `Name` row uses `24px` horizontal panel padding, `20px` vertical padding, a `240px` label area, `72px` label-to-field gap, and a `360px x 36px` input so the implemented row rhythm stays on the 4px spacing grid. Mobile uses the `440px` frame with `16px` horizontal content padding, `20px` top content padding, a full-width `408px` Settings column, `16px` title-to-panel gap, and a `408px x 96px` panel where the `Name` label and `376px x 36px` input stack with an `8px` gap.
  - **Figma tokenization:** The Settings desktop frame binds the `Knowledge / Layout` collection to `Desktop` mode and the Settings mobile frame binds it to `Mobile` mode. Settings layout dimensions and spacing use `layout/settings/*` variables for content width, page padding, page gap, panel padding, field gap, label width, and input width. The implemented Tailwind theme tokens mirror those dimensions and keep Settings spacing, padding, and field rhythm on the 4px grid. The Settings page header uses the shared `layout/page/header-height`, `typography/page/title/font-size`, and `typography/page/title/line-height` variables instead of Settings-local title dimensions. The sectioned panel binds fill, stroke, and radius to `color/surface/card`, `color/border/subtle`, and `radius/surface`. Text fills bind to `color/text/default`. The content, column, panel, and row frames use auto-layout with `FILL` or `HUG` sizing wherever their parent relationship allows.
  - **Field scope:** The page exposes only `Name`. The value is initialized from Logto profile `name`; if no `name` exists, the input starts empty while account identity fallback remains available from email or user id.
  - **Input behavior:** The field autosaves on blur and on Enter. Enter prevents form submission navigation and commits the current value. Escape restores the last saved value for the current focus session.
  - **Change detection:** The frontend trims the submitted value and skips the update request when the normalized value matches the last saved normalized value.
  - **Clearing name:** An empty normalized value is sent to the BFF as `name: null`, which clears the Logto display name. The shell and Settings page then fall back to email or user id for display.
  - **BFF profile endpoint:** The BFF exposes `GET /web-api/auth/profile` and `PATCH /web-api/auth/profile` as browser-visible authenticated profile endpoints under the existing auth route group. `GET` returns the current browser-safe Logto account profile. `PATCH` accepts JSON `{ "name": string | null }`, validates that string values are at most Logto's `128` character profile-name limit after trimming, requires an authenticated web session, and returns browser-safe authenticated profile data after Logto accepts the update.
  - **Logto Account API adapter:** The BFF Logto adapter requests the Account API access needed for user profile scope, calls Logto `GET /api/my-account` for profile reads, and calls `PATCH /api/my-account` with only the `name` field for updates. Server-side Logto Account API calls use the configured internal Logto endpoint while forwarding the browser-visible Logto host and protocol. If Logto rejects the cached user access token, the BFF clears the SDK access-token cache and retries once before treating the session as unauthenticated.
  - **Session/profile consistency:** The Settings page uses the BFF profile query for the field value. A successful profile update updates the Settings profile query and the shared shell session display cache without a full page reload. The BFF profile update response is shaped from the Logto Account API profile result.
  - **Error handling:** Unauthenticated updates return `401` with a machine-readable web error code. Invalid names return `400`. Logto authorization failures return `401` or `403` without exposing token details. Logto service or network failures return a generic web error response. Profile load failures render a persistent content-area notification and do not render an empty disabled profile form. The frontend keeps the edited value visible on save failure, marks the input with a red border and accessible invalid state, and shows the error message in a persistent content-area notification instead of inline field text.
  - **Notification behavior:** Save failures render a compact error notification anchored near the top-right of the Settings content area on desktop and below the page header on mobile. The notification stays visible until the user dismisses it, a later save succeeds, or the user leaves the route. Successful saves update the field and shell account display without a persistent success notification in the normal state.
  - **Save status:** The default and saved states do not render a visible saved label. Saving state must not introduce a section header or persistent status copy; any temporary pending affordance must preserve the normal panel geometry.
  - **Visual language:** Normal, saving, success, and error states keep the Figma layout quiet and avoid adding a save button. Default-state explanatory copy is omitted. Error feedback must not expand the settings row or place explanatory text directly below the input.
- **Interactions:**
  - Visiting `/settings` loads the current BFF profile query.
  - Editing `Name`, then blurring the field, commits the normalized value.
  - Pressing Enter while focused commits the normalized value.
  - Pressing Escape before commit restores the last saved value.
  - A successful commit updates the Settings field and shared shell account display from the returned profile data.
  - A failed commit leaves focusable controls usable, preserves the attempted value, marks the field invalid, and displays a content-area error notification.
  - Anonymous or expired-session direct visits start interactive sign-in through the shared web auth coordinator and return to `/settings` after successful authentication.

## Validation
- **Checks:**
  - `/settings` renders inside the shared shell and matches the approved desktop and mobile Settings Figma structures for the normal authenticated state.
  - `/settings` uses the shared routed-page header height and title typography tokens.
  - `/settings` does not add `Settings` to primary navigation.
  - Anonymous or expired-session direct visits start interactive sign-in through the shared web auth coordinator with `/settings` as the sign-in return path and do not render the editable profile form before authentication.
  - The Name input initializes from authenticated Logto profile data loaded through `GET /web-api/auth/profile`.
  - Profile load failures render content-area error notification feedback instead of an empty disabled profile form.
  - Blur and Enter each trigger exactly one save when the normalized value changed.
  - Unchanged normalized values do not call the update endpoint.
  - Empty normalized input sends `name: null`.
  - Successful updates refresh both the Settings field and shell account display without a full page reload.
  - Failed updates preserve the attempted value, mark the field invalid, and render content-area error notification feedback without expanding the settings row.
  - Browser code calls only `/web-api/*` and never receives Logto access tokens.
  - BFF tests cover authenticated profile read success, authenticated update success, unauthenticated profile rejection, invalid name rejection, Logto authorization failure mapping, and Logto service failure mapping.
  - BFF tests cover Account API profile reads and updates using the configured internal Logto endpoint with browser-visible forwarded host and protocol headers.
  - BFF tests cover clearing the cached user access token and retrying once when Logto rejects the first Account API request.
  - Frontend tests cover authenticated rendering, anonymous rendering, blur autosave, Enter autosave, unchanged no-op behavior, Escape reset, success propagation, invalid field styling, persistent error notification behavior, and absence of persistent saved-status copy in the normal state.
- **Evidence:**
  - Active specs describe Logto as the account profile authority and the BFF as the only browser-visible account update boundary.
  - Targeted web BFF and frontend tests pass for the profile update workflow.
  - Browser-level visual inspection confirms desktop and mobile Settings page alignment with the approved Figma frames.
