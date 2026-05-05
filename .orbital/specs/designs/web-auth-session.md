---
abstract: Web BFF authentication and session design for browser-safe Logto login, silent session recovery, protected-route login, token refresh, and session security.
out_of_scope: Logto tenant provisioning, public MCP bearer-token authentication, account-profile field layout, Dashboard token lifecycle UI, and Workspace review authorization.
---

# Design: web-auth-session

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the shared web authentication and session boundary so browser users get modern login recovery while Logto tokens remain server-side.
- **Scope/Boundaries:** Covers browser web session state, BFF Logto session storage, interactive sign-in, public-route silent SSO recovery, protected-route sign-in, session expiration, token refresh, sign-out, CSRF protection, session cookie policy, and browser auth-state coordination. Excludes public MCP bearer-token authentication, Logto tenant setup, account settings field layout, Dashboard PAT lifecycle behavior, and Workspace contribution-role authorization.
- **Related Requirements:** R-001, R-003, R-004, R-006, R-007, R-008.

## Constraint Projection
- **Governing Constraints:** Public web authentication is owned by the web BFF boundary, browser code uses same-origin BFF endpoints, browser runtime state never receives Logto access tokens or refresh tokens, public routes stay usable for anonymous visitors, protected web surfaces require authenticated sessions, and behavior-changing auth/session decisions stay synchronized in active specs.
- **Detail Commitments:** The browser stores only BFF-owned cookies for web authentication and quota identity. Logto ID tokens, access tokens, refresh tokens, authorization transaction data, and token caches are stored only in the BFF server session backed by Redis. The BFF session cookie is `knowledge.sid`, `HttpOnly`, `SameSite=Lax`, secure in production, and scoped without a Domain attribute unless deployment configuration explicitly requires one. Authenticated web sessions use a rolling idle lifetime of `30` days and an absolute lifetime of `90` days. Public routes attempt at most one silent SSO recovery per browser tab session before continuing anonymously. Protected routes start interactive sign-in automatically when no valid web session exists.
- **Update Rule:** Repository-level public/private boundary requirements remain stable while BFF auth route contracts, frontend auth coordinator behavior, cookie/session lifetime, silent SSO mechanics, token refresh behavior, and CSRF rules stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Browser route navigation to public and protected web routes.
  - Browser requests to `/web-api/auth/*` and other `/web-api/*` endpoints.
  - BFF-owned `knowledge.sid` session cookie.
  - Redis-backed Express session state for Logto SDK storage.
  - Logto authorization, callback, token, Account API, and sign-out responses.
  - Browser `Origin` or `Referer` headers on state-changing web requests.
- **Outputs:**
  - Browser-safe web session responses containing only anonymous/authenticated status and safe user display fields.
  - Interactive Logto redirects for protected-route and explicit sign-in flows.
  - Silent SSO iframe completion messages for public-route session recovery.
  - Safe machine-readable auth errors for expired or missing sessions.
  - Destroyed local BFF session state on stale callback state, unrecoverable expiration, and sign-out.
- **Artifacts:**
  - `apps/web/server/auth/logto.ts`
  - `apps/web/server/auth/routes.ts`
  - `apps/web/server/auth/sessionState.ts`
  - `apps/web/server/session/redisSessionStore.ts`
  - `apps/web/server/app.ts`
  - `apps/web/server/index.ts`
  - `apps/web/src/app/providers.tsx`
  - `apps/web/src/app/router.tsx`
  - `apps/web/src/app/AppShell.tsx`
  - `apps/web/src/shared/web-api/client.ts`
  - `apps/web/src/shared/web-api/session.ts`
  - `apps/web/src/shared/web-api/sessionQueries.ts`
  - `apps/web/src/shared/web-api/useWebSession.ts`
  - Auth coordinator/provider modules under `apps/web/src/shared/web-api/` or `apps/web/src/app/`.
  - Targeted BFF route tests, frontend coordinator tests, and route guard tests.

## Design Approach
- **Approach:** Web authentication uses a BFF-first architecture with a single auth/session coordinator. The BFF is the only holder of Logto tokens and the only boundary that talks to Logto. The frontend resolves one shared browser-safe auth state, performs one silent public-route SSO attempt when useful, automatically starts interactive sign-in for protected routes, and handles session expiration consistently across every BFF call.
- **Key Elements:**
  - **Browser token boundary:** Browser JavaScript never receives Logto ID tokens, access tokens, refresh tokens, client secrets, Management API credentials, or MCP service tokens. Browser code calls same-origin `/web-api/*` endpoints with credentials included.
  - **BFF token storage:** The Logto SDK storage adapter persists Logto SDK keys in the Express session. Redis is the durable session store. Access-token cache entries are server-side session data and are never serialized into browser runtime configuration or JSON responses.
  - **Session cookie policy:** The web session cookie is `knowledge.sid`, `HttpOnly`, `SameSite=Lax`, and `Secure` whenever `KNOWLEDGE_WEB_COOKIE_SECURE=true`. Production configuration sets secure cookies. Cookie Domain remains unset by default so the browser scopes the cookie to the web host. Cross-subdomain cookie sharing is not part of the baseline web session contract.
  - **Session lifetime:** The BFF web session uses rolling idle expiration of `30` days. Each valid authenticated BFF request refreshes the idle timeout. The session also stores an absolute creation timestamp and expires after `90` days regardless of activity. Unauthenticated anonymous quota cookies are governed separately by the quota design and do not extend authenticated web sessions.
  - **Session fixation protection:** The BFF regenerates the Express session id when an interactive or silent Logto callback successfully authenticates a user. Return-path state and Logto transaction state required to complete the callback are preserved across the regeneration. Sign-out clears Logto SDK storage and destroys the local BFF session after the Logto sign-out URL has been computed.
  - **Session response contract:** `GET /web-api/auth/session` returns only `{ status: "anonymous" }` or `{ status: "authenticated", user }` with safe display fields. It does not expose provider tokens, token expiration timestamps, refresh state, Logto raw claims, or internal session metadata.
  - **Auth cache policy:** `/web-api/auth/*` responses use `Cache-Control: no-store` and ignore conditional request validators so browser auth state, callback results, and profile reads are never represented by `304 Not Modified` responses.
  - **Frontend auth coordinator:** The web client has one shared auth coordinator/provider backed by the session query. It exposes `checking`, `anonymous`, `silent-checking`, `authenticated`, `expired`, and `error` browser states to route guards and feature components. Feature pages consume this coordinator for auth state so network errors, expired sessions, and true anonymous state remain distinct.
  - **Public routes:** `/overview`, `/graph`, `/graph/<canonical-lcc-slug-path>`, `/search`, and `/docs` remain usable without login. On a public route, if the session response is anonymous and the current browser tab has not already attempted silent SSO for the active app load, the coordinator starts one silent SSO attempt. Silent SSO success updates the shared session state without disrupting the route. Silent SSO failure leaves the route anonymous and keeps normal public-page interactions available.
  - **Protected routes:** `/dashboard`, `/workspace`, and `/settings` are protected account routes. If the shared auth state is anonymous or expired after the initial session check, the coordinator automatically starts interactive sign-in with the current route as `return_to`. These routes do not own page-local anonymous sign-in prompts as their primary access behavior.
  - **Auth endpoint contract:** `GET /web-api/auth/session` remains the browser-safe session read endpoint. `POST /web-api/auth/sign-in` starts top-level interactive sign-in. `GET /web-api/auth/callback` completes top-level interactive sign-in. `POST /web-api/auth/silent-sign-in` starts iframe-targeted silent SSO. `GET /web-api/auth/silent-callback` completes silent SSO and returns only a same-origin postMessage completion document. `POST /web-api/auth/sign-out` signs out and destroys local session state. `GET /web-api/auth/profile` and `PATCH /web-api/auth/profile` remain authenticated account-profile endpoints.
  - **Explicit sign-in:** The shell `Sign in` action and feature-level sign-in-required dialogs remain available on public routes. They start interactive sign-in through the BFF with a same-origin relative `return_to` value. Invalid, external, protocol-relative, oversized, or `/web-api/*` return paths fall back to `/`.
  - **Interactive sign-in transport:** Interactive sign-in starts through a BFF-owned POST form submission to `/web-api/auth/sign-in` so same-origin form behavior and return-path validation remain the shared entry point. Route guards may create and submit this form programmatically. The browser-visible sign-in surface exposes only this POST form entry point.
  - **Silent SSO transport:** Silent SSO starts through a BFF-owned hidden form targeting a hidden iframe. The BFF initiates a Logto authorization request with prompt-none semantics and a dedicated silent callback redirect URI. The silent callback completes the Logto transaction, updates the server-side session on success, and returns a small same-origin HTML response that posts a success or safe failure message to the parent window. The parent window accepts messages only from the configured same-origin web base URL. Each Logto app used by the web BFF must register both the interactive callback URI and the silent callback URI for its environment.
  - **Silent SSO isolation:** Silent authorization transaction data is isolated from interactive authorization transaction data so a silent public-route attempt cannot overwrite an in-progress interactive login. If the Logto SDK cannot isolate concurrent authorization transactions directly, the BFF serializes auth attempts per session and cancels or ignores stale silent attempts when interactive sign-in starts.
  - **Silent SSO fallback:** Browser third-party-cookie, iframe, frame-ancestors, provider, or prompt-none failures are non-fatal on public routes. The coordinator records the attempt for the tab session and continues anonymously. Protected routes do not depend on iframe silent SSO; they use top-level interactive sign-in.
  - **Callback handling:** Interactive callback consumes BFF-stored `return_to` and redirects with `303` to the validated path. Stale, missing, invalid, or mismatched callback transaction state is treated as a recoverable auth restart condition: the BFF clears local session state and redirects safely to the validated `return_to` path or `/` without exposing provider details or stack traces. Silent callback does not top-level redirect; it sends a postMessage completion document to the parent window and never renders application UI.
  - **Token refresh:** Logto-dependent BFF operations use a shared server-side token resolver. When Logto rejects a cached user access token, the resolver clears the cached access token and retries token acquisition once. If refresh succeeds, the original BFF operation continues. If Logto still rejects the token, the BFF treats the session as expired, clears local authenticated session state, and returns a safe auth error.
  - **Auth error contract:** BFF endpoints return `401` with machine-readable auth codes for missing or expired sessions. `authentication_required` indicates no valid authenticated web session is present. `session_expired` indicates the session cannot be refreshed or has exceeded idle or absolute lifetime. Token details, provider responses, stack traces, raw claims, and internal endpoint names are not returned to the browser.
  - **Global browser 401 handling:** The shared web API JSON client recognizes auth error codes. On `authentication_required` or `session_expired`, it clears shared session/profile caches, preserves current route state, and notifies the auth coordinator. Protected routes start interactive sign-in. Public feature mutations preserve user drafts and show a sign-in-required or session-expired recovery path.
  - **Draft preservation:** Feature flows that collect user input before authenticated submission keep local draft state when a BFF mutation returns an auth error. After the user signs in and returns to the route, the feature may let the user resubmit the preserved draft if the component still owns that state.
  - **CSRF and origin protection:** State-changing `/web-api/*` requests require same-origin request validation. The BFF accepts requests with an `Origin` matching the configured public web origin. When `Origin` is absent, the BFF may fall back to a same-origin `Referer` check. Requests that fail same-origin validation return a safe `403` without invoking feature handlers. JSON mutations continue using same-origin fetch with credentials included; form-backed auth actions rely on browser-sent origin metadata plus SameSite cookies.
  - **Sign-out:** Sign-out is a POST action protected by the same origin checks. The BFF computes the Logto sign-out redirect, clears local Logto SDK storage, destroys the Express session, clears the session cookie, and redirects to the configured public base URL or a validated post-logout path.
  - **Dependency failure handling:** Temporary Logto or Redis dependency failures do not silently convert authenticated users into anonymous users on public pages. The coordinator represents dependency failure as an error state when the session cannot be checked. Protected routes show a recoverable auth-unavailable state instead of looping through sign-in.
  - **Observability:** BFF logs include safe auth event categories such as session check failure, silent SSO failure, token refresh retry, session expired, CSRF rejection, and sign-out completion. Logs do not include token values, authorization codes, raw cookies, or raw Logto claims.
- **Interactions:**
  - Browser loads a public route and requests `/web-api/auth/session`.
  - If authenticated, the coordinator exposes authenticated user state to shell and features.
  - If anonymous, the coordinator attempts one hidden-iframe silent SSO check for the tab session.
  - Silent success refreshes `/web-api/auth/session` and updates account UI without changing the route.
  - Silent failure marks the tab attempt complete and continues with anonymous public UI.
  - Browser loads a protected route and requests `/web-api/auth/session`.
  - If unauthenticated or expired, the coordinator posts to `/web-api/auth/sign-in` with `return_to` set to the current route.
  - Interactive callback completes Logto auth, regenerates the session id, stores Logto tokens server-side, and redirects to `return_to`.
  - A protected BFF mutation detects stale cached access token, clears the server-side access-token cache, retries once, and either continues or returns `session_expired`.
  - Browser receives `session_expired`, clears session cache, preserves route and draft state, and starts the appropriate recovery path.

## Validation
- **Checks:**
  - Browser session responses never include Logto tokens, authorization codes, refresh-token state, raw claims, client secrets, service tokens, or internal session metadata.
  - Auth route responses are not conditionally cached and do not return `304` for session state.
  - Session cookie options are `HttpOnly`, `SameSite=Lax`, and environment-controlled `Secure`, with no Domain attribute unless explicitly configured.
  - Session middleware tests cover rolling idle expiration, absolute expiration, expired-session cleanup, session id regeneration after successful callback, stale callback cleanup, and local session destruction on sign-out.
  - BFF auth route tests cover interactive sign-in return-path validation, invalid return-path fallback, callback redirect, silent sign-in success postMessage response, silent sign-in safe failure response, and isolation between silent and interactive auth attempts.
  - BFF token resolver tests cover cached access-token rejection, one clear-and-retry refresh attempt, refresh success continuation, refresh failure mapping to `session_expired`, and safe error bodies.
  - BFF CSRF/origin tests cover accepted same-origin POST/PATCH requests, accepted same-origin Referer fallback, rejected cross-origin mutations, and no feature-handler invocation after rejection.
  - Frontend auth coordinator tests cover initial checking state, public-route silent SSO success, public-route silent SSO failure with anonymous continuation, one-attempt-per-tab behavior, protected-route auto sign-in, explicit sign-in preserving return path, session-expired recovery, dependency error state, and no infinite redirect loops.
  - Feature tests cover Search/Graph proposal draft preservation on auth errors and protected route behavior for Dashboard, Workspace, and Settings.
  - Browser-level smoke tests cover public anonymous access, public silent SSO recovery when a Logto SSO session exists, protected-route automatic sign-in, callback return to original route, sign-out, and expired-session recovery.
- **Evidence:**
  - Active specs describe `web-auth-session` as the owner of browser web authentication and session behavior.
  - Targeted BFF and frontend auth tests pass.
  - Browser verification confirms public routes remain accessible without login and protected routes automatically start sign-in.
