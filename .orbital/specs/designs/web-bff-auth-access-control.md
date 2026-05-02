---
abstract: Public web BFF, Logto session, anonymous identity, authenticated suggestion submission, quota, and private API access-control design for the web application.
out_of_scope: MCP server implementation, backend domain ranking semantics, suggestion review UI, and Logto tenant provisioning runbooks.
---

# Design: web-bff-auth-access-control

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the public web access boundary so browser users can use Graph View and Search anonymously with strict quotas, signed-in users can submit Search card edit suggestions and manage Dashboard tokens through the BFF, and browser code cannot call private service APIs as public product interfaces.
- **Scope/Boundaries:** Covers the `apps/web` Express BFF runtime, browser-visible web API endpoints, Logto server-side session handling, authenticated card suggestion submission, Logto Account API profile access for web account settings, Logto Management API orchestration for Dashboard tokens, anonymous identity cookies, Redis-backed quota state, private API calls, MCP internal usage summary calls, public route exposure, and first-version validation expectations. Excludes MCP public tool implementation, backend search ranking semantics, review-workbench UI, and operational Logto tenant setup instructions.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Public browser access must use explicit public web surfaces, internal backend API integration must remain contract-driven, module boundaries must prevent hidden coupling, runtime behavior must be reproducible across Docker environments, and active specs must stay synchronized with behavior-changing access-boundary decisions.
- **Detail Commitments:** `apps/web` runs an Express BFF that serves built Vite assets and owns `/web-api/*` plus auth redirect endpoints. Browser-side code calls only BFF-owned web endpoints for application data, card suggestion submission, and account profile updates. The BFF calls private FastAPI endpoints over Docker-network HTTP using the generated internal API client from `packages/contracts`. The BFF derives card suggestion user identity from the authenticated Logto session and does not accept browser-supplied user identity fields. The BFF calls Logto Account API endpoints server-side for authenticated account profile reads and updates. The BFF calls Logto Management API server-side for signed-in users' Dashboard token lifecycle operations. The BFF calls the MCP service's internal usage-summary endpoint for Dashboard usage aggregates. Production Nginx routes the public application host to `web` and does not expose `/api/v1/*` as a public REST API surface. Logto access tokens are held server-side, not in browser runtime state. Redis stores web sessions and quota counters under web-owned key prefixes.
- **Update Rule:** Requirement-level public/private boundary constraints remain stable while endpoint paths, quota policy details, Redis key layout, and Logto SDK wiring stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Browser requests to the public application host.
  - Logto redirects and authorization-code callback parameters.
  - Secure browser cookies for the web session and anonymous identity.
  - Redis session records and quota counter records.
  - Generated internal API client and generated internal API types.
  - Private FastAPI endpoints reachable from `web` through Docker service DNS.
  - Logto Account API for authenticated account profile reads and updates.
  - Logto Management API for signed-in users' personal access token lifecycle operations.
  - MCP internal usage-summary endpoint reachable from `web` through the internal service network.
- **Outputs:**
  - Built React application assets served by the Express BFF.
  - Browser-visible auth/session endpoints.
  - Browser-visible account profile read and update endpoints.
  - Browser-visible web data endpoints for route-addressable Graph View, Search, authenticated Search card suggestion submission, and Dashboard token management.
  - Internal API requests sent only from the BFF to the private API service.
  - Logto Account API and Management API requests sent only from the BFF.
  - MCP internal usage-summary requests sent only from the BFF, authenticated with a service-to-service bearer access token, and containing PAT fingerprints instead of raw token values.
  - Quota response metadata and `429` responses when limits are exceeded.
- **Artifacts:**
  - `apps/web` server runtime source.
  - `apps/web` React client adapters for `/web-api/*`.
  - `infra/docker/web/Dockerfile`.
  - `infra/compose/docker-compose.base.yml`, `infra/compose/docker-compose.dev.yml`, `infra/compose/docker-compose.prod.yml`, and environment templates.
  - `infra/docker/nginx/default.conf`.

## Design Approach
- **Approach:** The web application uses a public Express BFF as the only browser data boundary. The BFF performs session resolution, anonymous identity assignment, quota checks, Dashboard token orchestration, and internal API orchestration before returning web-facing JSON responses. FastAPI remains the private domain/API service and continues to own internal OpenAPI contracts. Public programmatic search is governed by the separate Logto-authenticated MCP surface defined in `mcp-public-search.md`.
- **Key Elements:**
  - **Public web host:** The public application host serves the React app and `/web-api/*` through the `web` BFF. Nginx does not publish private FastAPI REST routes as public product endpoints.
  - **BFF runtime:** `apps/web` uses Node.js and Express. The production process serves the built Vite assets and handles web API and auth routes from the same container.
  - **Auth routes:** The BFF owns Logto sign-in, callback, session, account profile, and sign-out routes. The shell auth action starts sign-in through the BFF, not through a browser-side Logto SDK.
  - **Server-side Logto session:** The BFF completes the authorization-code flow with Logto, stores session and token material server-side in Redis, and sends the browser only a secure httpOnly session cookie. Browser-side code observes login state through a BFF session endpoint.
  - **Post-login return path:** `POST /web-api/auth/sign-in` accepts an optional form `return_to` value from same-origin app routes. The BFF accepts only relative paths on the configured public origin, rejects external URLs and `/web-api/*` API paths, stores the validated path in the server-side session, and consumes it after a successful Logto callback. Missing or invalid values fall back to `/`.
  - **Logto endpoint split:** The BFF keeps the public Logto endpoint as the OAuth issuer and browser redirect base. When container networking requires a different service-to-service target, the BFF may use a separate internal Logto endpoint for server-side HTTP requests, including discovery, token exchange, account calls, and JWKS retrieval for ID token verification, while forwarding the public host and protocol to Logto.
  - **Server-side Logto account profile:** The BFF uses the authenticated server-side Logto session to request the Account API access needed for profile scope. Browser-visible profile reads and updates are shaped as safe session/profile JSON and never expose Logto tokens.
  - **Anonymous identity:** Anonymous users receive a high-entropy anonymous identity cookie. The cookie contains no personal data and is used only as a quota principal. The BFF may issue it on the first browser request that needs quota tracking.
  - **Quota principals:** Logged-in users are counted by Logto `sub`. Anonymous users are counted by anonymous identity and also checked against an IP hard-protection principal. Logged-in requests are also eligible for an IP-level abuse ceiling.
  - **Quota policy shape:** First-version quotas count requests, with all protected web endpoints using `cost=1`. The quota interface accepts `cost` so later endpoints can consume weighted quota without changing the BFF boundary. Policy supports default quotas plus explicit taxonomy-view overrides for anonymous, authenticated, and IP protection principals.
  - **Current BFF web quota env contract:** Web quota configuration is owned by first-class required environment variables, not JSON blobs or code defaults. Default protected web routes, including Search, use anonymous `20/minute` and `200/day`, authenticated `120/minute` and `2000/day`, and IP `240/minute` and `5000/day`. Graph View taxonomy routes use explicit `KNOWLEDGE_WEB_TAXONOMY_VIEW_*` env overrides because a normal leaf session can issue viewport layout, title hydration, detail hydration, path, and node requests: anonymous `60/minute` and `600/day`, authenticated `240/minute` and `5000/day`, and IP `600/minute` and `15000/day`.
  - **Quota windows:** The BFF enforces at least one short burst window and one longer total-use window. Redis counter keys use web-owned prefixes, TTLs aligned with their windows, and principal/route dimensions sufficient for default and endpoint-specific policies.
  - **Web auth endpoints:** The BFF exposes `GET /web-api/auth/session` for browser-readable session state, `POST /web-api/auth/sign-in` for starting Logto sign-in with optional validated `return_to` form state, `GET /web-api/auth/callback` for the Logto redirect callback, `GET /web-api/auth/profile` and `PATCH /web-api/auth/profile` for authenticated Settings profile reads and updates, and `POST /web-api/auth/sign-out` for clearing the server-side session and browser cookie.
  - **Web data endpoints:** The BFF exposes `GET /web-api/search` for the Search page, `GET /web-api/taxonomy/view/root` for Graph View root child-list state, `GET /web-api/taxonomy/view/path` for Graph View root state through the empty taxonomy route path, `GET /web-api/taxonomy/view/path/{route_path}` for canonical LCC slug-path Graph View state with nested path capture, `GET /web-api/taxonomy/view/nodes/{node_id}` for id-addressed taxonomy view access, `GET /web-api/taxonomy/view/leaves/{node_id}/layout` for viewport-scoped leaf layout slices, `POST /web-api/taxonomy/view/leaves/{node_id}/titles` for viewport-scoped title hydration, and `POST /web-api/taxonomy/view/leaves/{node_id}/details` for viewport-scoped leaf card hydration.
  - **Suggested-edit endpoint:** The BFF exposes authenticated `POST /web-api/cards/{node_id}/suggested-edits` for Search card suggestion submission. The browser request body contains `base_version`, `suggested_title`, and `suggested_content`. The BFF supplies `suggested_by_user_id` from the server-side Logto session before calling the private API.
  - **Dashboard endpoints:** The BFF exposes authenticated Dashboard token endpoints under `/web-api/dashboard/tokens` for list/create/rename and `/web-api/dashboard/tokens/delete` for delete. Token names are carried in request bodies rather than URL path segments. Dashboard endpoint request, response, error, copy-token, and usage fallback details are defined in `web-dashboard-token-management.md`.
  - **Internal route mapping:** `GET /web-api/search` maps to private `GET /api/v1/search`. `POST /web-api/cards/{node_id}/suggested-edits` maps to private `POST /api/v1/cards/{node_id}/suggested-edits`. `GET /web-api/taxonomy/view/root` maps to private `GET /api/v1/taxonomy/view/root`. `GET /web-api/taxonomy/view/path` maps to private `GET /api/v1/taxonomy/view/path/` with an empty route path. `GET /web-api/taxonomy/view/path/{route_path}` maps to private `GET /api/v1/taxonomy/view/path/{route_path:path}`. `GET /web-api/taxonomy/view/nodes/{node_id}` maps to private `GET /api/v1/taxonomy/view/nodes/{node_id}`. `GET /web-api/taxonomy/view/leaves/{node_id}/layout` maps to private `GET /api/v1/taxonomy/view/leaves/{node_id}/layout`. `POST /web-api/taxonomy/view/leaves/{node_id}/titles` maps to private `POST /api/v1/taxonomy/view/leaves/{node_id}/titles`. `POST /web-api/taxonomy/view/leaves/{node_id}/details` maps to private `POST /api/v1/taxonomy/view/leaves/{node_id}/details`.
  - **Private internal API:** FastAPI remains reachable to repository services on Docker networks and local development host ports. It is not a public product API in production.
  - **Error responses:** Quota failures return `429` with `Retry-After` when available and a machine-readable web error code. Invalid or expired sessions are treated as anonymous when the endpoint permits anonymous use. Authenticated-only suggestion submission returns `401` when no valid session is present. Internal API failures are mapped to web responses without exposing internal stack traces.
  - **MCP boundary:** External programmatic search access is owned by the MCP server with Logto personal-access-token authentication. The BFF does not act as the public programmatic API for external clients.
  - **Dashboard usage boundary:** Dashboard usage aggregates are read by the BFF from the internal MCP usage-summary endpoint with Logto service-to-service bearer authentication. The BFF sends PAT fingerprints only, never raw token values, and does not directly read MCP usage database tables.
- **Interactions:**
  - Browser loads the app from `web`, then calls `/web-api/auth/session` to render the current auth state.
  - Anonymous sign-in form submissions include the current app route as `return_to` when available. The BFF validates and stores that value in the server-side session before redirecting to Logto.
  - Anonymous browser data requests receive or reuse an anonymous identity cookie, pass quota checks, and are forwarded by the BFF to the private API.
  - Logged-in browser data requests resolve the server-side Logto session, pass the higher logged-in quota policy, and are forwarded by the BFF to the private API.
  - Logged-in Search suggestion requests resolve the server-side Logto session, attach the Logto user id as `suggested_by_user_id`, and are forwarded by the BFF to the private suggested-edit API.
  - Logged-in Dashboard token requests resolve the server-side Logto session, call Logto Management API for the current user's PAT lifecycle state, call MCP internal usage summary for token usage aggregates, and return Dashboard-specific JSON to the browser.
  - Settings profile reads and updates resolve the authenticated server-side Logto session, read or patch the user's Logto Account API profile, and return refreshed browser-safe profile state.
  - The BFF uses Redis for session state and quota counters and uses Docker DNS for private API access.
  - Public Logto redirects return to BFF callback routes, where callback state is validated before a session cookie is issued. After successful callback handling, the BFF redirects to the consumed validated return path or `/`.

## Validation
- **Checks:**
  - Production Nginx config exposes the web host, Logto hosts, and accepted webhook paths without exposing `/api/v1/*` as a public route.
  - Browser-side application code calls `/web-api/*` for Search and Graph View data, uses the path-addressed taxonomy endpoint for route restoration, and does not receive private API runtime configuration.
  - Browser-side Dashboard code calls only `/web-api/dashboard/*` and does not receive Logto Management API credentials, MCP internal endpoint configuration, PAT fingerprints, or private database configuration.
  - BFF server tests cover anonymous identity issuance, Logto session state resolution, validated post-login return paths, external and BFF API return path fallback, sign-out session clearing, default quota enforcement, endpoint-specific quota override behavior, burst-window rejection, long-window rejection, and `Retry-After` response behavior.
  - BFF server tests cover account profile read success, account profile update success, unauthenticated account profile rejection, invalid account profile input, and Logto Account API failure mapping.
  - BFF server tests cover authenticated card suggestion forwarding, unauthenticated card suggestion rejection, and absence of browser-supplied user identity in forwarded suggestion payloads.
  - BFF Dashboard tests cover authenticated token list/create/rename/delete orchestration, safe error mapping, Logto Management API adapter behavior, MCP usage-summary adapter behavior, and raw-token redaction from logs and errors.
  - BFF internal API adapter tests verify generated client usage and error mapping for Search, suggested-edit creation, and taxonomy view calls.
  - BFF taxonomy view route tests verify nested slash-path forwarding for `GET /web-api/taxonomy/view/path/{route_path}` and preserve private API unresolved-path errors without converting them to root responses.
  - Frontend tests cover auth action rendering, anonymous state rendering, logged-in state rendering, quota error presentation, and existing Graph View/Search data-loading behavior through web adapters.
  - Compose/config tests verify `web` receives internal API, Redis, Logto, cookie, PAT fingerprint, Logto Management API, and MCP usage-summary settings while the browser runtime does not receive the private API base URL, Logto Management API credentials, MCP internal endpoints, PAT fingerprints, or PAT fingerprint secret.
  - Contract drift checks continue to validate the private FastAPI OpenAPI artifacts consumed by the BFF.
- **Evidence:**
  - Active specs describe the public web BFF boundary, private API boundary, and MCP boundary without conflicting route exposure claims.
  - Targeted backend/web tests pass for BFF auth, quota, internal API adapters, and frontend data adapters.
  - Nginx and compose configuration inspection confirms the public route and Docker-network boundaries.
