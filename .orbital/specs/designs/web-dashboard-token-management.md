---
abstract: Authenticated web dashboard design for Logto personal access token lifecycle management, MCP usage summaries, and account quota visibility.
out_of_scope: Public MCP tool behavior, Logto tenant provisioning runbooks, billing policy, and backend graph/search ranking semantics.
---

# Design: web-dashboard-token-management

## Active Truth Policy
- Keep only currently accepted dashboard decisions in this active document.
- Remove superseded decisions instead of preserving transition or migration narratives.
- If a dashboard behavior decision is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the authenticated Dashboard page where signed-in web users manage Logto personal access tokens for MCP access, inspect token-level MCP usage, and see account-level MCP search quota.
- **Scope/Boundaries:** Covers browser-facing dashboard UI behavior, BFF dashboard endpoints, Logto personal access token Management API orchestration, MCP usage summary reads, MCP account quota summary reads, token lifecycle actions, copy behavior, and validation expectations. Excludes public MCP protocol behavior, Logto tenant setup, billing/plan policy, and private graph/search ranking semantics.
- **Related Requirements:** R-001, R-003, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Dashboard access is a public web surface owned by the web BFF, browser integration uses BFF-owned endpoints, internal service access remains behind server-side boundaries, module ownership remains explicit, and behavior-changing page/API decisions stay synchronized in active specs.
- **Detail Commitments:** The Dashboard route is an authenticated account-menu web route rendered inside the shared app shell. The browser calls only `/web-api/dashboard/*`. The BFF resolves the signed-in Logto web session, uses server-side Logto Management API credentials to manage the current user's personal access tokens, computes MCP PAT fingerprints without exposing raw tokens to MCP, calls internal MCP Dashboard endpoints for token-level usage aggregates and account-level quota summary, and returns dashboard-specific JSON to the browser. The dashboard follows Figma file `WBYs6P9HMxe21TSYQL637r`, node `247:50`, current desktop frame `702:5336`, current mobile frame `702:5503`, current desktop create-token-dialog frame `702:5682`, and current mobile create-token-dialog frame `702:5848`.
- **Update Rule:** Repository-level public/private boundary requirements remain stable while dashboard endpoint paths, Logto Management API orchestration, MCP usage summary shape, MCP quota summary shape, token lifecycle UI behavior, and dashboard visual structure stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Signed-in browser requests to `/dashboard`.
  - Browser API requests to `/web-api/dashboard/*`.
  - Server-side Logto web session state resolved by the BFF.
  - Logto Management API responses for the current user's personal access tokens, including token `name`, `value`, `createdAt`, and `expiresAt`.
  - MCP internal usage-summary responses keyed by PAT fingerprint.
  - MCP internal quota-summary responses keyed by signed-in Logto user subject.
  - Browser clipboard requests triggered by explicit copy controls.
- **Outputs:**
  - Dashboard page showing account MCP quota, token name, token value, usage count, and last-used state.
  - Dashboard dialogs for creating, renaming, and deleting tokens.
  - Dashboard JSON responses scoped to the signed-in user.
  - Server-side Logto Management API mutations for create, rename, and delete.
  - MCP usage-summary requests containing PAT fingerprints instead of raw PAT values.
  - MCP quota-summary requests containing the signed-in user subject and no token values.
- **Artifacts:**
  - `apps/web/server/routes/dashboardTokens.ts`
  - `apps/web/server/dashboard/logtoPersonalAccessTokens.ts`
  - `apps/web/server/dashboard/mcpUsageSummary.ts`
  - `apps/web/server/dashboard/mcpQuotaSummary.ts`
  - `apps/web/server/dashboard/patFingerprint.ts`
  - `apps/web/src/features/dashboard/pages/index.tsx`
  - `apps/web/src/features/dashboard/data/dashboardTokens.ts`
  - `apps/web/src/features/dashboard/components/*`
  - `apps/mcp/src/knowledge_mcp/usage/summary.py`
  - `apps/mcp/src/knowledge_mcp/http_app.py`
  - Targeted tests under `apps/web/server`, `apps/web/src/features/dashboard`, and `apps/mcp/tests`.

## Design Approach
- **Approach:** The Dashboard remains a BFF-first web account surface. The web BFF owns the browser contract and composes two server-side sources: Logto Management API for token lifecycle state and MCP's internal Dashboard endpoints for usage and quota aggregates. The MCP service continues to own MCP usage persistence, quota state, and read-model semantics; it exposes internal summary endpoints for the BFF, not public browser APIs and not MCP tools.
- **Key Elements:**
  - **Authentication gate:** Dashboard data endpoints require an authenticated web session. Anonymous requests receive a safe unauthenticated response and do not create, list, rename, or delete tokens.
  - **Browser endpoint ownership:** Browser code calls `/web-api/dashboard/tokens` for token list/create/rename operations and `/web-api/dashboard/tokens/delete` for token deletion. Browser code never places token names in URL path segments and never calls Logto Management API, MCP internal endpoints, MCP databases, or private FastAPI routes directly.
  - **Browser quota endpoint:** Browser code calls `/web-api/dashboard/quota` for account-level MCP search quota summary. The endpoint requires an authenticated web session and returns `{ quota: { daily, weekly }, quotaAvailable }`. Each quota window contains `used`, `limit`, `remaining`, `windowSeconds`, `startedAt`, and `resetAt`.
  - **Browser list contract:** `GET /web-api/dashboard/tokens` requires an authenticated web session and returns `{ tokens, usageAvailable }`. Each token row contains `name`, `tokenValue`, `maskedToken`, `usageCount`, `lastUsedAt`, `createdAt`, and `expiresAt`. `usageCount` and `lastUsedAt` are nullable only when MCP usage summary is unavailable; tokens with no recorded usage return `usageCount: 0` and `lastUsedAt: null`.
  - **Browser mutation contract:** `POST /web-api/dashboard/tokens` accepts `{ name }` and creates a Logto PAT. `PATCH /web-api/dashboard/tokens` accepts `{ currentName, name }` and renames the current token name to the submitted name. `POST /web-api/dashboard/tokens/delete` accepts `{ name }` and deletes that token. Successful mutations return the refreshed `{ tokens, usageAvailable }` directory response.
  - **Browser error contract:** Dashboard endpoints return `401 dashboard_auth_required` for missing sessions, `400 dashboard_invalid_token_name` for invalid names, `404 dashboard_token_not_found` for missing tokens, `409 dashboard_token_name_conflict` for duplicate names, and `503 dashboard_token_service_unavailable` when Logto token lifecycle calls cannot be completed. MCP usage-summary failure does not fail the token directory; the BFF returns tokens with `usageAvailable: false`, `usageCount: null`, and `lastUsedAt: null`.
  - **Logto PAT lifecycle:** The BFF uses configured server-side Logto Management API credentials to call Logto user personal-access-token endpoints for the signed-in user's Logto subject. List and mutation responses are the authoritative source for active token names, raw token values, creation timestamps, and expiration timestamps. Rename uses Logto `PATCH /api/users/{userId}/personal-access-tokens` with body `{ currentName, name }`.
  - **Token value exposure:** Dashboard list and mutation responses include token values returned by Logto so the authenticated owner can copy each token from the table, matching the approved Figma surface. The BFF does not persist raw token values and does not create a repository-owned shadow secret store. Raw token values are never written to logs, MCP usage tables, Redis quota keys, error responses, or durable web-owned storage. Tests must avoid snapshotting real-looking token values.
  - **Fingerprint contract:** The canonical PAT fingerprint contract is owned by the MCP service because MCP owns token-level usage attribution and account quota state. The fingerprint is `pat_` plus lowercase hexadecimal HMAC-SHA256 of the raw PAT bytes using the active PAT fingerprint secret as UTF-8 bytes. The web BFF implements the same algorithm from its own runtime configuration and must not import `apps/mcp/src/**`.
  - **Fingerprint secret:** The runtime has exactly one active PAT fingerprint secret shared by configuration between the web BFF and MCP service. The web BFF setting is `KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET`; the MCP setting is `KNOWLEDGE_MCP_PAT_FINGERPRINT_SECRET`. Both values must match and must be at least 32 characters. Dual-secret rotation is not supported by the baseline contract.
  - **Fingerprint join:** The BFF computes PAT fingerprints from Logto-returned token values, then sends only fingerprints to the MCP internal usage-summary endpoint. Raw PAT values are not sent to MCP for summary reads. PAT fingerprints are internal join keys and are not returned to the browser.
  - **MCP usage summary:** MCP exposes `POST /internal/dashboard/usage-summary` over the internal service network. The endpoint requires a Logto-issued service-to-service bearer access token for the configured MCP internal API resource and `usage:read` scope. The request body is `{ patFingerprints: string[] }`; invalid fingerprints or batch size above the configured maximum return `400`. The response body is `{ summaries: [{ patFingerprint, successfulSearchCount, lastUsedAt }] }` and includes one summary per requested unique fingerprint. Missing usage returns `successfulSearchCount: 0` and `lastUsedAt: null`. It is not routed as a public MCP endpoint and is not listed as an MCP tool.
  - **MCP quota summary:** MCP exposes `POST /internal/dashboard/quota-summary` over the internal service network. The endpoint requires a Logto-issued service-to-service bearer access token for the configured MCP internal API resource and `usage:read` scope. The request body is `{ userSub: string }`. The response body is `{ quota: { daily, weekly } }`; daily quota is `1,000` MCP search calls per `24` hours from first use, and weekly quota is `5,000` MCP search calls per `7` days from first use. Inactive windows return `used: 0`, `remaining: limit`, `startedAt: null`, and `resetAt: null`.
  - **Usage count:** The dashboard `usage` column shows lifetime successful `search` tool calls per token. It is computed from MCP usage events where `tool_name = "search"` and `status = "success"`.
  - **Last used:** The dashboard `last used` column shows the latest recorded MCP usage-event timestamp for the token. Tokens with no MCP usage render an explicit unused state.
  - **Quota panel:** The dashboard renders a `Quota` section above the token directory. The left quota metric is `Daily` and the right quota metric is `Weekly`. The primary value renders `used / limit`. Active windows render reset copy such as `resets in 18h` or `resets in 5d`; inactive windows render `starts on first use`. The browser does not display route-limit internals, Redis keys, PAT fingerprints, or web BFF quota state.
  - **Create flow:** The `Create Token` button opens a Figma-aligned dialog with a required token name input. On success, the created token appears in the directory and its value is copyable from the row. Duplicate or invalid names return safe field-level errors.
  - **Rename flow:** Each token row exposes a compact row action for rename. Rename opens a dialog with the current name prefilled, submits to the BFF, and refreshes the token directory after success.
  - **Delete flow:** Each token row exposes a destructive delete action behind confirmation. Delete removes the Logto PAT and refreshes the token directory after success. Usage history remains in MCP usage records. Deleted tokens are excluded from the active token directory.
  - **Copy flow:** The row copy control copies the token value currently returned by the BFF for that authenticated owner. Copy success and failure are reflected through local UI state without sending token values back to the server.
  - **Desktop layout:** The desktop Dashboard follows the shared `320px` sidebar shell and renders a `Dashboard` page header, a quota section, and a large card-like token directory with the `Create Token` action in the token section header. The directory uses a table layout with columns for `Name`, `Token`, `Usage`, `Last used`, and compact row actions.
  - **Mobile layout:** The mobile Dashboard renders inside the shared mobile shell with the same content hierarchy as desktop. Token rows collapse into stacked row cards that preserve name, token, copy, usage, last-used, and row actions without horizontal overflow. Dialogs use centered mobile surfaces with scrim, close control, field body, and two-button footer matching the approved create-token dialog frame.
  - **Visual language:** Dashboard styling follows the approved Knowledge Figma variables: light page background, translucent/card white surfaces, subtle blue-gray borders, `8px` radii, Geist typography, restrained spacing, and lucide icons for copy/menu/close/actions.
  - **Loading and empty states:** Loading states preserve the directory geometry. Empty authenticated state renders the token directory with no rows and keeps `Create Token` as the primary action. Error states avoid displaying internal endpoint names, raw tokens, credentials, stack traces, or PAT fingerprints.
- **Interactions:**
  - User opens `/dashboard`; the route loads dashboard data through the BFF.
  - BFF resolves the current Logto session, fetches the user's PAT list from Logto, computes fingerprints, requests MCP usage summaries, requests MCP quota summary for the signed-in user subject, and returns dashboard JSON to the browser.
  - User creates a token; BFF creates the Logto PAT, refreshes usage summary for the directory state, and returns the updated row set.
  - User copies a token; browser clipboard receives the row token value without a server round trip.
  - User renames a token; BFF updates the Logto PAT name and refreshes the directory.
  - User deletes a token; BFF deletes the Logto PAT and refreshes the directory.

## Validation
- **Checks:**
  - Dashboard browser code calls only `/web-api/dashboard/*` for dashboard data and mutations.
  - Unauthenticated dashboard API requests cannot list, create, rename, or delete tokens.
  - Unauthenticated dashboard API requests cannot read account quota.
  - BFF route tests cover list, create, rename, delete, duplicate-name error mapping, invalid-name error mapping, Logto dependency failure mapping, MCP summary dependency failure mapping, and raw-token redaction from error responses.
  - BFF Logto adapter tests verify Management API paths, current-user scoping, server-side credential use, and no browser-exposed Management API tokens.
  - BFF MCP summary adapter tests verify service-to-service bearer authentication, request batch validation, only PAT fingerprints are sent to MCP for usage reads, only user subject is sent to MCP for quota reads, and raw PAT values are not sent.
  - MCP summary endpoint tests verify service authentication, per-fingerprint filtering, lifetime successful search-call counts, latest usage timestamp semantics, zero-count rows for fingerprints without usage, user-subject quota summary reads, inactive-window semantics, and absence of raw PAT values in responses.
  - Frontend tests cover dashboard loading, quota panel rendering, inactive quota windows, empty state, token table rendering, mobile row rendering, create dialog, rename dialog, delete confirmation, copy control behavior, authenticated error handling, and account-menu navigation.
  - Architecture tests verify `apps/web` does not import `apps/mcp/src/**`, does not import `apps/api/src/**`, and does not directly connect to MCP usage database tables.
  - Visual inspection confirms desktop and mobile Dashboard composition matches the approved Figma structures without horizontal overflow.
- **Evidence:**
  - Active specs describe Dashboard as a BFF-first authenticated web surface.
  - Targeted web BFF, MCP summary, and frontend dashboard tests pass.
  - MCP usage persistence remains owned by `apps/mcp`; Dashboard reads usage through an internal summary endpoint rather than cross-app table access.
