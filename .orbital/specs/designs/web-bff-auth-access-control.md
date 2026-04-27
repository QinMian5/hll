---
abstract: Public web BFF, Logto session, anonymous identity, quota, and private API access-control design for the web application.
out_of_scope: MCP server implementation, backend domain ranking semantics, and Logto tenant provisioning runbooks.
---

# Design: web-bff-auth-access-control

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the public web access boundary so browser users can use Graph View and Search anonymously with strict quotas, can sign in with Logto for higher quotas, and cannot call private FastAPI service APIs as public product interfaces.
- **Scope/Boundaries:** Covers the `apps/web` Express BFF runtime, browser-visible web API endpoints, Logto server-side session handling, anonymous identity cookies, Redis-backed quota state, private API calls, public route exposure, and first-version validation expectations. Excludes MCP server implementation, backend search ranking semantics, and operational Logto tenant setup instructions.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Public browser access must use explicit public web surfaces, internal backend API integration must remain contract-driven, module boundaries must prevent hidden coupling, runtime behavior must be reproducible across Docker environments, and active specs must stay synchronized with behavior-changing access-boundary decisions.
- **Detail Commitments:** `apps/web` runs an Express BFF that serves built Vite assets and owns `/web-api/*` plus auth redirect endpoints. Browser-side code calls only BFF-owned web endpoints for application data. The BFF calls private FastAPI endpoints over Docker-network HTTP using the generated internal API client from `packages/contracts`. Production Nginx routes the public application host to `web` and does not expose `/api/v1/*` as a public REST API surface. Logto access tokens are held server-side, not in browser runtime state. Redis stores web sessions and quota counters under web-owned key prefixes.
- **Update Rule:** Requirement-level public/private boundary constraints remain stable while endpoint paths, quota policy details, Redis key layout, and Logto SDK wiring stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Browser requests to the public application host.
  - Logto redirects and authorization-code callback parameters.
  - Secure browser cookies for the web session and anonymous identity.
  - Redis session records and quota counter records.
  - Generated internal API client and generated internal API types.
  - Private FastAPI endpoints reachable from `web` through Docker service DNS.
- **Outputs:**
  - Built React application assets served by the Express BFF.
  - Browser-visible auth/session endpoints.
  - Browser-visible web data endpoints for Graph View and Search.
  - Internal API requests sent only from the BFF to the private API service.
  - Quota response metadata and `429` responses when limits are exceeded.
- **Artifacts:**
  - `apps/web` server runtime source.
  - `apps/web` React client adapters for `/web-api/*`.
  - `infra/docker/web/Dockerfile`.
  - `infra/compose/docker-compose.base.yml`, `infra/compose/docker-compose.dev.yml`, `infra/compose/docker-compose.prod.yml`, and environment templates.
  - `infra/docker/nginx/default.conf`.

## Design Approach
- **Approach:** The web application uses a public Express BFF as the only browser data boundary. The BFF performs session resolution, anonymous identity assignment, quota checks, and internal API orchestration before returning web-facing JSON responses. FastAPI remains the private domain/API service and continues to own internal OpenAPI contracts. Public programmatic search is governed by the separate Logto-authenticated MCP surface defined in `mcp-public-search.md`.
- **Key Elements:**
  - **Public web host:** The public application host serves the React app and `/web-api/*` through the `web` BFF. Nginx does not publish private FastAPI REST routes as public product endpoints.
  - **BFF runtime:** `apps/web` uses Node.js and Express. The production process serves the built Vite assets and handles web API and auth routes from the same container.
  - **Auth routes:** The BFF owns Logto sign-in, callback, session, and sign-out routes. The shell auth action starts sign-in through the BFF, not through a browser-side Logto SDK.
  - **Server-side Logto session:** The BFF completes the authorization-code flow with Logto, stores session and token material server-side in Redis, and sends the browser only a secure httpOnly session cookie. Browser-side code observes login state through a BFF session endpoint.
  - **Anonymous identity:** Anonymous users receive a high-entropy anonymous identity cookie. The cookie contains no personal data and is used only as a quota principal. The BFF may issue it on the first browser request that needs quota tracking.
  - **Quota principals:** Logged-in users are counted by Logto `sub`. Anonymous users are counted by anonymous identity and also checked against an IP hard-protection principal. Logged-in requests are also eligible for an IP-level abuse ceiling.
  - **Quota policy shape:** First-version quotas count requests, with all protected web endpoints using `cost=1`. The quota interface accepts `cost` so later endpoints can consume weighted quota without changing the BFF boundary. Policy supports a default quota plus endpoint-specific overrides.
  - **Quota windows:** The BFF enforces at least one short burst window and one longer total-use window. Redis counter keys use web-owned prefixes, TTLs aligned with their windows, and principal/route dimensions sufficient for default and endpoint-specific policies.
  - **Web auth endpoints:** The BFF exposes `GET /web-api/auth/session` for browser-readable session state, `POST /web-api/auth/sign-in` for starting Logto sign-in, `GET /web-api/auth/callback` for the Logto redirect callback, and `POST /web-api/auth/sign-out` for clearing the server-side session and browser cookie.
  - **Web data endpoints:** The BFF exposes `GET /web-api/search` for the Search page, `GET /web-api/taxonomy/view/root` for Graph View root state, `GET /web-api/taxonomy/view/nodes/{node_id}` for branch or leaf drill-down state, and `POST /web-api/taxonomy/view/leaves/{node_id}/details` for viewport-scoped leaf card hydration.
  - **Internal route mapping:** `GET /web-api/search` maps to private `GET /api/v1/search`. `GET /web-api/taxonomy/view/root` maps to private `GET /api/v1/taxonomy/view/root`. `GET /web-api/taxonomy/view/nodes/{node_id}` maps to private `GET /api/v1/taxonomy/view/nodes/{node_id}`. `POST /web-api/taxonomy/view/leaves/{node_id}/details` maps to private `POST /api/v1/taxonomy/view/leaves/{node_id}/details`.
  - **Private internal API:** FastAPI remains reachable to repository services on Docker networks and local development host ports. It is not a public product API in production.
  - **Error responses:** Quota failures return `429` with `Retry-After` when available and a machine-readable web error code. Invalid or expired sessions are treated as anonymous when the endpoint permits anonymous use. Internal API failures are mapped to web responses without exposing internal stack traces.
  - **MCP boundary:** External programmatic search access is owned by the MCP server with Logto personal-access-token authentication. The BFF does not act as the public programmatic API for external clients.
- **Interactions:**
  - Browser loads the app from `web`, then calls `/web-api/auth/session` to render the current auth state.
  - Anonymous browser data requests receive or reuse an anonymous identity cookie, pass quota checks, and are forwarded by the BFF to the private API.
  - Logged-in browser data requests resolve the server-side Logto session, pass the higher logged-in quota policy, and are forwarded by the BFF to the private API.
  - The BFF uses Redis for session state and quota counters and uses Docker DNS for private API access.
  - Public Logto redirects return to BFF callback routes, where callback state is validated before a session cookie is issued.

## Validation
- **Checks:**
  - Production Nginx config exposes the web host, Logto hosts, and accepted webhook paths without exposing `/api/v1/*` as a public route.
  - Browser-side application code calls `/web-api/*` for Search and Graph View data and does not receive private API runtime configuration.
  - BFF server tests cover anonymous identity issuance, Logto session state resolution, sign-out session clearing, default quota enforcement, endpoint-specific quota override behavior, burst-window rejection, long-window rejection, and `Retry-After` response behavior.
  - BFF internal API adapter tests verify generated client usage and error mapping for Search and taxonomy view calls.
  - Frontend tests cover auth action rendering, anonymous state rendering, logged-in state rendering, quota error presentation, and existing Graph View/Search data-loading behavior through web adapters.
  - Compose/config tests verify `web` receives internal API, Redis, Logto, and cookie settings while the browser runtime does not receive the private API base URL.
  - Contract drift checks continue to validate the private FastAPI OpenAPI artifacts consumed by the BFF.
- **Evidence:**
  - Active specs describe the public web BFF boundary, private API boundary, and MCP boundary without conflicting route exposure claims.
  - Targeted backend/web tests pass for BFF auth, quota, internal API adapters, and frontend data adapters.
  - Nginx and compose configuration inspection confirms the public route and Docker-network boundaries.
