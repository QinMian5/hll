---
abstract: Implementation plan for upgrading the web app into an Express BFF with Logto session auth, anonymous/authenticated quotas, and private internal API access.
out_of_scope: Public REST API exposure, MCP search implementation, API-side Logto authorization, weighted quota accounting beyond the reserved cost interface, and unrelated compose file renaming.
---

# Web BFF Auth Access Control Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents are available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-04-26-web-bff-auth-access-control-plan`

**Goal:** Convert `apps/web` from a browser-only Vite SPA into a server-backed web service that serves the React client, owns Logto-backed web sessions, applies anonymous/authenticated request quotas, and calls the private FastAPI service only from Docker-internal server code.

**Architecture:** A Node.js Express BFF serves Vite-built static assets and owns all browser-facing `/web-api/*` endpoints. Browser code no longer calls `/api/v1/*` or imports the generated backend client at runtime. The BFF uses server-side Logto session state, Redis-backed session/quota storage, an anonymous identity cookie plus IP hard-protection, and a typed internal API client that calls FastAPI over Docker DNS (`http://api:8000`). Production nginx exposes the web BFF, Logto, and webhook receivers only; it does not expose the backend API.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/web-bff-auth-access-control.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/00-system-definition.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/01-system-modules.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/03-architecture-constraints.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/05-technology-stack-selection.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/06-deployment-docker.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/web-app-shell-navigation.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-shell.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

**Assumptions and Constraints:**
- Anonymous users can use current Search and Graph View surfaces with strict request-count limits.
- Authenticated Logto users receive higher request-count limits.
- The quota interface must accept a `cost` value, but every endpoint uses `cost=1` in this implementation.
- Quotas include at least one short burst window and one longer total-use window.
- Quotas use a unified default policy plus route-group overrides for Search and taxonomy view routes.
- Authenticated users still receive an IP-level abuse ceiling.
- The browser stores only httpOnly cookies for BFF session and anonymous identity; no Logto access token is exposed to browser JavaScript.
- The BFF consumes private backend APIs through typed contract artifacts and explicit route handlers, not a transparent proxy.
- The implementation updates the repository's current compose files at `infra/compose/docker-compose.*.yml`. Any future rename to `compose.*.yml` is separate work.
- Code and comments are English.

**Decision Gates:** None open. The accepted design is: explicit Express BFF endpoints, server-side Logto sessions, Redis-backed session/quota state, private internal FastAPI access, no public `/api/v1/*`, and MCP search left for a later Logto-authenticated surface.

**Tech Stack:**
- Node.js + Express
- Vite middleware in development and Vite-built static assets in production
- React 19 + TypeScript
- `@logto/express` / `@logto/node`
- `express-session`, `cookie-parser`, `connect-redis`, `redis`
- `openapi-fetch` with generated `@knowledge/contracts` types
- Vitest + Supertest
- Docker Compose + nginx

---

## File Structure Map

### Web package, build, and server entrypoint
- Modify: `/Users/mianqin/Code/knowledge/apps/web/package.json`
- Modify: `/Users/mianqin/Code/knowledge/pnpm-lock.yaml`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/tsconfig.json`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/tsconfig.node.json`
- Create: `/Users/mianqin/Code/knowledge/apps/web/tsconfig.server.json`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/vite.config.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/index.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/app.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/staticAssets.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/config.ts`
- Test: `/Users/mianqin/Code/knowledge/apps/web/server/app.test.ts`

### Auth, sessions, anonymous identity, and quota
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/auth/logto.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/auth/routes.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/auth/sessionState.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/session/redisSessionStore.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/access/anonymousIdentity.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/access/principal.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/access/quotaPolicy.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/access/quotaStore.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/access/quotaMiddleware.ts`
- Test: `/Users/mianqin/Code/knowledge/apps/web/server/auth/routes.test.ts`
- Test: `/Users/mianqin/Code/knowledge/apps/web/server/access/anonymousIdentity.test.ts`
- Test: `/Users/mianqin/Code/knowledge/apps/web/server/access/quotaMiddleware.test.ts`

### Internal API and BFF routes
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/internal-api/client.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/internal-api/errors.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/routes/search.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/server/routes/taxonomyView.ts`
- Test: `/Users/mianqin/Code/knowledge/apps/web/server/routes/search.test.ts`
- Test: `/Users/mianqin/Code/knowledge/apps/web/server/routes/taxonomyView.test.ts`

### Browser-side web API adapters and shell auth action
- Delete or repurpose away from browser runtime: `/Users/mianqin/Code/knowledge/apps/web/src/shared/api/contractsClient.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/shared/config/index.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/shared/config/index.test.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/shared/web-api/client.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/shared/web-api/errors.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/shared/web-api/session.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/app/AppShell.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/app/AppShell.test.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/search/data/searchQueries.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.test.ts`

### Docker, nginx, env, and infra tests
- Modify: `/Users/mianqin/Code/knowledge/infra/docker/web/Dockerfile`
- Modify: `/Users/mianqin/Code/knowledge/infra/docker/nginx/default.conf`
- Modify: `/Users/mianqin/Code/knowledge/infra/compose/docker-compose.base.yml`
- Modify: `/Users/mianqin/Code/knowledge/infra/compose/docker-compose.dev.yml`
- Modify: `/Users/mianqin/Code/knowledge/infra/compose/docker-compose.prod.yml`
- Modify: `/Users/mianqin/Code/knowledge/infra/env/.env.example`
- Modify: `/Users/mianqin/Code/knowledge/infra/env/.env.dev`
- Modify: `/Users/mianqin/Code/knowledge/infra/env/.env.prod`
- Modify: `/Users/mianqin/Code/knowledge/infra/env/.env.test`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/core/test_prod_nginx_config.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/core/test_compose_conventions.py`
- Existing env alignment test: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/core/test_env_file_alignment.py`

### Spec synchronization
- Modify only if implementation discovers a necessary contract correction:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/web-bff-auth-access-control.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/06-deployment-docker.md`

## Chunk 1: Express BFF Build and Runtime Foundation

### Task T01: Replace Vite preview with one Express web service

**Task ID:** `T01`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `apps/web/package.json`
- Modify: `pnpm-lock.yaml`
- Modify: `apps/web/tsconfig.json`
- Modify: `apps/web/tsconfig.node.json`
- Create: `apps/web/tsconfig.server.json`
- Modify: `apps/web/vite.config.ts`
- Create: `apps/web/server/index.ts`
- Create: `apps/web/server/app.ts`
- Create: `apps/web/server/staticAssets.ts`
- Create: `apps/web/server/config.ts`
- Test: `apps/web/server/app.test.ts`
- Modify: `infra/docker/web/Dockerfile`

- [ ] **Step 1: Add server dependencies and scripts**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web add express @logto/express express-session cookie-parser connect-redis redis openapi-fetch
pnpm --filter web add -D @types/express @types/express-session @types/cookie-parser supertest @types/supertest tsx
pnpm --filter web remove @logto/react
```

Update scripts:

```json
{
  "dev": "tsx watch server/index.ts",
  "build": "tsc -b && vite build --outDir dist/client",
  "preview": "node dist/server/index.js",
  "start": "node dist/server/index.js"
}
```

- [ ] **Step 2: Add server TypeScript build configuration**

Add `apps/web/tsconfig.server.json` with Node ESM output to `dist/server` and include only `server/**/*.ts`.

Required compiler overrides:
- `noEmit: false`
- `allowImportingTsExtensions: false`
- `module: "NodeNext"`
- `moduleResolution: "NodeNext"`
- `lib: ["ES2023"]`
- `types: ["node"]`

Update `apps/web/tsconfig.json` references to include `tsconfig.server.json`.

- [ ] **Step 3: Remove Vite `/api` proxy enforcement**

Update `apps/web/vite.config.ts` so Vite no longer requires `API_PROXY_TARGET` or `VITE_API_BASE_URL`, and no longer proxies `/api`.

The development BFF owns the public port and uses Vite middleware internally.

- [ ] **Step 4: Create Express app and static/Vite integration**

Implement:
- `createApp(options)` in `server/app.ts`;
- runtime config loading in `server/config.ts`;
- dev Vite middleware mounting in non-production;
- production static asset serving from `dist/client`;
- SPA fallback to `index.html` after `/web-api/*` routes;
- `index.ts` listening on `KNOWLEDGE_WEB_HOST` and `KNOWLEDGE_WEB_PORT`.

Required config keys:
- `KNOWLEDGE_WEB_HOST`
- `KNOWLEDGE_WEB_PORT`
- `KNOWLEDGE_WEB_PUBLIC_BASE_URL`
- `KNOWLEDGE_WEB_INTERNAL_API_BASE_URL`
- `KNOWLEDGE_WEB_REDIS_URL`
- `KNOWLEDGE_WEB_SESSION_SECRET`
- `KNOWLEDGE_WEB_COOKIE_SECURE`
- `KNOWLEDGE_WEB_COOKIE_DOMAIN`
- `KNOWLEDGE_WEB_LOGTO_ENDPOINT`
- `KNOWLEDGE_WEB_LOGTO_APP_ID`
- `KNOWLEDGE_WEB_LOGTO_APP_SECRET`
- quota settings introduced in T03.

- [ ] **Step 5: Update Docker web runtime**

Update `infra/docker/web/Dockerfile`:
- dev target still exposes `5173`, but runs the Express BFF dev script;
- prod target builds Vite client and server output;
- prod target exposes `4173`;
- prod command runs `pnpm start`, not `vite preview`.

- [ ] **Step 6: Verify BFF foundation**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web run build
pnpm --filter web exec vitest --run server/app.test.ts
```

Expected:
- build emits `apps/web/dist/client` and `apps/web/dist/server`;
- focused server test passes once added;
- no Vite config error requires API proxy env.

- [ ] **Step 7: Controller finalizes task**

Confirm:
- one Express process owns web serving in dev and prod;
- Vite preview is not the deployment runtime;
- the browser runtime has no private API base URL setting.

Commit message shape:
- `[plan:2026-04-26-web-bff-auth-access-control-plan][task:T01] add Express web runtime foundation`

## Chunk 2: Logto Session, Anonymous Identity, and Quota Enforcement

### Task T02: Implement server-side Logto session routes

**Task ID:** `T02`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `apps/web/server/auth/logto.ts`
- Create: `apps/web/server/auth/routes.ts`
- Create: `apps/web/server/auth/sessionState.ts`
- Create: `apps/web/server/session/redisSessionStore.ts`
- Modify: `apps/web/server/app.ts`
- Modify: `apps/web/server/config.ts`
- Test: `apps/web/server/auth/routes.test.ts`

- [ ] **Step 1: Inspect installed Logto Express types**

After dependency installation, inspect:

```bash
cd /Users/mianqin/Code/knowledge
sed -n '1,220p' apps/web/node_modules/@logto/express/lib/index.d.ts
```

Implementation requirement:
- public product contract remains `/web-api/auth/*`;
- if `@logto/express` helper routes cannot be configured to those paths, wrap the SDK or use its lower-level `@logto/node` dependency;
- do not expose `/logto/*` as the browser contract.

- [ ] **Step 2: Add failing auth route tests**

Test cases:
- `GET /web-api/auth/session` returns an anonymous payload without exposing tokens;
- `POST /web-api/auth/sign-in` redirects to Logto sign-in flow;
- `GET /web-api/auth/callback` completes session callback behavior through mocked SDK boundary;
- `POST /web-api/auth/sign-out` clears session and redirects or returns a redirect target;
- cookies are `httpOnly`, `SameSite=Lax`, and `Secure` when configured.

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run server/auth/routes.test.ts
```

Expected: FAIL before implementation.

- [ ] **Step 3: Implement session middleware and Redis store**

Implement:
- `express-session` with `connect-redis`;
- Redis URL from `KNOWLEDGE_WEB_REDIS_URL`;
- session key prefix distinct from quota keys;
- no token/session material returned to browser JSON;
- `trust proxy` only when configured for production proxy deployment.

- [ ] **Step 4: Implement auth route contract**

Routes:
- `GET /web-api/auth/session`
- `POST /web-api/auth/sign-in`
- `GET /web-api/auth/callback`
- `POST /web-api/auth/sign-out`

Session response shape:

```ts
type WebSessionResponse =
  | { readonly status: "anonymous" }
  | {
      readonly status: "authenticated";
      readonly user: {
        readonly id: string;
        readonly name?: string;
        readonly email?: string;
      };
    };
```

- [ ] **Step 5: Re-run auth route tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run server/auth/routes.test.ts
```

Expected: PASS.

- [ ] **Step 6: Controller finalizes task**

Confirm:
- the browser sees only session status/user metadata;
- Logto server session is BFF-owned;
- route paths match the approved `/web-api/auth/*` contract.

Commit message shape:
- `[plan:2026-04-26-web-bff-auth-access-control-plan][task:T02] add Logto-backed web session routes`

### Task T03: Implement anonymous identity and Redis-backed quota middleware

**Task ID:** `T03`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `apps/web/server/access/anonymousIdentity.ts`
- Create: `apps/web/server/access/principal.ts`
- Create: `apps/web/server/access/quotaPolicy.ts`
- Create: `apps/web/server/access/quotaStore.ts`
- Create: `apps/web/server/access/quotaMiddleware.ts`
- Modify: `apps/web/server/app.ts`
- Modify: `apps/web/server/config.ts`
- Test: `apps/web/server/access/anonymousIdentity.test.ts`
- Test: `apps/web/server/access/quotaMiddleware.test.ts`

- [ ] **Step 1: Add failing anonymous identity and quota tests**

Test cases:
- anonymous requests without identity cookie receive a stable httpOnly anonymous identity cookie;
- anonymous principal uses `anonymous:<id>` plus IP hard-protection;
- authenticated principal uses Logto `sub` plus IP hard-protection;
- quota store increments by `cost`;
- this release always passes `cost=1`;
- both burst and long-window limits are checked;
- route overrides can apply to Search without changing taxonomy defaults;
- exceeded quota returns HTTP `429`, `Retry-After`, and safe JSON error.

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run \
  server/access/anonymousIdentity.test.ts \
  server/access/quotaMiddleware.test.ts
```

Expected: FAIL before implementation.

- [ ] **Step 2: Implement anonymous identity cookie**

Cookie requirements:
- generated with cryptographically strong random bytes;
- httpOnly;
- `SameSite=Lax`;
- `Secure` when `KNOWLEDGE_WEB_COOKIE_SECURE=true`;
- long-lived enough for anonymous quota continuity;
- not readable by browser JavaScript.

- [ ] **Step 3: Implement quota policy and Redis store**

Add config keys:
- `KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX`
- `KNOWLEDGE_WEB_ANON_BURST_LIMIT`
- `KNOWLEDGE_WEB_ANON_BURST_WINDOW_SECONDS`
- `KNOWLEDGE_WEB_ANON_TOTAL_LIMIT`
- `KNOWLEDGE_WEB_ANON_TOTAL_WINDOW_SECONDS`
- `KNOWLEDGE_WEB_AUTH_BURST_LIMIT`
- `KNOWLEDGE_WEB_AUTH_BURST_WINDOW_SECONDS`
- `KNOWLEDGE_WEB_AUTH_TOTAL_LIMIT`
- `KNOWLEDGE_WEB_AUTH_TOTAL_WINDOW_SECONDS`
- `KNOWLEDGE_WEB_IP_BURST_LIMIT`
- `KNOWLEDGE_WEB_IP_BURST_WINDOW_SECONDS`
- `KNOWLEDGE_WEB_IP_TOTAL_LIMIT`
- `KNOWLEDGE_WEB_IP_TOTAL_WINDOW_SECONDS`
- optional route override JSON or explicit per-route envs only if needed by current endpoints.

Redis key pattern must be distinct from sessions, for example:

```text
knowledge:web:quota:{window}:{routeGroup}:{principalHash}
```

Do not store raw IPs or user IDs directly when hashing is simple and sufficient.

- [ ] **Step 4: Wire quota middleware to web data routes only**

Apply quotas to:
- `GET /web-api/search`
- `GET /web-api/taxonomy/view/root`
- `GET /web-api/taxonomy/view/nodes/:nodeId`
- `POST /web-api/taxonomy/view/leaves/:nodeId/details`

Do not rate-limit static assets with this application quota middleware.

- [ ] **Step 5: Re-run quota tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run \
  server/access/anonymousIdentity.test.ts \
  server/access/quotaMiddleware.test.ts
```

Expected: PASS.

- [ ] **Step 6: Controller finalizes task**

Confirm:
- anonymous access works but is strongly limited;
- authenticated access has higher limits;
- IP ceiling applies to both anonymous and authenticated requests;
- cost weighting is structurally reserved without changing current request-count behavior.

Commit message shape:
- `[plan:2026-04-26-web-bff-auth-access-control-plan][task:T03] add anonymous and authenticated quota enforcement`

## Chunk 3: Explicit BFF Data Routes and Internal FastAPI Client

### Task T04: Add typed BFF routes for Search and taxonomy view

**Task ID:** `T04`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `apps/web/server/internal-api/client.ts`
- Create: `apps/web/server/internal-api/errors.ts`
- Create: `apps/web/server/routes/search.ts`
- Create: `apps/web/server/routes/taxonomyView.ts`
- Modify: `apps/web/server/app.ts`
- Test: `apps/web/server/routes/search.test.ts`
- Test: `apps/web/server/routes/taxonomyView.test.ts`

- [ ] **Step 1: Add failing BFF route tests**

Test cases:
- `GET /web-api/search?query=...` calls internal `GET /api/v1/search`;
- `GET /web-api/taxonomy/view/root` calls internal `GET /api/v1/taxonomy/view/root`;
- `GET /web-api/taxonomy/view/nodes/:nodeId` calls internal `GET /api/v1/taxonomy/view/nodes/{node_id}`;
- `POST /web-api/taxonomy/view/leaves/:nodeId/details` calls internal `POST /api/v1/taxonomy/view/leaves/{node_id}/details`;
- invalid route parameters return `400` from the BFF without calling FastAPI;
- internal non-2xx responses are mapped to safe browser errors;
- raw internal API origin is not returned to the browser.

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run \
  server/routes/search.test.ts \
  server/routes/taxonomyView.test.ts
```

Expected: FAIL before implementation.

- [ ] **Step 2: Implement internal API client**

Use:
- `openapi-fetch` as a direct web dependency;
- type-only imports from `@knowledge/contracts/generated/types`;
- `KNOWLEDGE_WEB_INTERNAL_API_BASE_URL`;
- no browser-visible base URL.

Avoid importing `apps/web/src/shared/api/contractsClient.ts` from server code.

- [ ] **Step 3: Implement explicit web routes**

Route mapping:

| Web route | Internal route |
| --- | --- |
| `GET /web-api/search` | `GET /api/v1/search` |
| `GET /web-api/taxonomy/view/root` | `GET /api/v1/taxonomy/view/root` |
| `GET /web-api/taxonomy/view/nodes/:nodeId` | `GET /api/v1/taxonomy/view/nodes/{node_id}` |
| `POST /web-api/taxonomy/view/leaves/:nodeId/details` | `POST /api/v1/taxonomy/view/leaves/{node_id}/details` |

Apply quota middleware per route group before calling internal API.

- [ ] **Step 4: Re-run BFF route tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run \
  server/routes/search.test.ts \
  server/routes/taxonomyView.test.ts
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- browser-facing routes are explicit;
- no transparent `/api` proxy exists in web server code;
- internal API calls are typed and private.

Commit message shape:
- `[plan:2026-04-26-web-bff-auth-access-control-plan][task:T04] add explicit BFF data routes`

## Chunk 4: Browser Client Migration to BFF Endpoints

### Task T05: Move browser data access from generated backend client to `/web-api/*`

**Task ID:** `T05`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Delete or remove browser use of: `apps/web/src/shared/api/contractsClient.ts`
- Modify: `apps/web/src/shared/config/index.ts`
- Modify: `apps/web/src/shared/config/index.test.ts`
- Create: `apps/web/src/shared/web-api/client.ts`
- Create: `apps/web/src/shared/web-api/errors.ts`
- Create: `apps/web/src/shared/web-api/session.ts`
- Modify: `apps/web/src/features/search/data/searchQueries.ts`
- Modify: `apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.ts`
- Modify: `apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.test.ts`
- Modify: `apps/web/src/app/AppShell.tsx`
- Modify: `apps/web/src/app/AppShell.test.tsx`

- [ ] **Step 1: Add failing browser adapter tests**

Test cases:
- search query adapter calls `/web-api/search`, not `/api/v1/search`;
- taxonomy root/node/detail adapters call `/web-api/taxonomy/view/*`;
- `VITE_API_BASE_URL` is no longer part of browser config;
- AppShell session action renders Sign in for anonymous session and Sign out/user state for authenticated session;
- browser code does not import `shared/api/contractsClient`.

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run \
  src/shared/config/index.test.ts \
  src/features/taxonomy-view/data/taxonomyViewQueries.test.ts \
  src/app/AppShell.test.tsx
```

Expected: FAIL before migration.

- [ ] **Step 2: Implement web API fetch wrapper**

Create a small browser wrapper that:
- uses same-origin relative URLs only;
- sends credentials with requests;
- parses safe JSON errors;
- never reads or exposes Logto tokens.

- [ ] **Step 3: Update Search and taxonomy query modules**

Preserve existing exported response types from `@knowledge/contracts/generated/types`.

Replace runtime calls:
- from generated backend client calls to `/api/v1/*`;
- to `fetch` wrapper calls against `/web-api/*`.

Keep leaf edge tuple normalization and type assertions.

- [ ] **Step 4: Implement session UI action**

Update AppShell:
- remove disabled Login placeholder;
- render a real Sign in POST action when anonymous;
- render authenticated user state and Sign out POST action when authenticated;
- keep GitHub disabled/no action unless a separate design asks otherwise.

- [ ] **Step 5: Verify no browser direct API imports remain**

Run:

```bash
cd /Users/mianqin/Code/knowledge
rg -n "VITE_API_BASE_URL|API_PROXY_TARGET|/api/v1|shared/api/contractsClient|@knowledge/contracts/generated/client" apps/web/src apps/web/vite.config.ts
```

Expected:
- no browser runtime references to `VITE_API_BASE_URL`, `API_PROXY_TARGET`, `/api/v1`, `shared/api/contractsClient`, or `@knowledge/contracts/generated/client`;
- type-only imports from `@knowledge/contracts/generated/types` are acceptable.

- [ ] **Step 6: Re-run browser focused tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web exec vitest --run \
  src/shared/config/index.test.ts \
  src/features/taxonomy-view/data/taxonomyViewQueries.test.ts \
  src/app/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Controller finalizes task**

Confirm:
- browser code consumes only BFF routes;
- browser-visible runtime config no longer names the backend API;
- auth UI reflects BFF session state without token exposure.

Commit message shape:
- `[plan:2026-04-26-web-bff-auth-access-control-plan][task:T05] move browser data access behind BFF`

## Chunk 5: Docker, nginx, and Environment Boundary Hardening

### Task T06: Make backend API Docker-internal and expose only BFF/webhook/Logto surfaces

**Task ID:** `T06`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `infra/compose/docker-compose.base.yml`
- Modify: `infra/compose/docker-compose.dev.yml`
- Modify: `infra/compose/docker-compose.prod.yml`
- Modify: `infra/docker/nginx/default.conf`
- Modify: `infra/env/.env.example`
- Modify: `infra/env/.env.dev`
- Modify: `infra/env/.env.prod`
- Modify: `infra/env/.env.test`
- Modify: `apps/api/tests/unit/core/test_prod_nginx_config.py`
- Modify: `apps/api/tests/unit/core/test_compose_conventions.py`

- [ ] **Step 1: Add failing infra tests for the new exposure boundary**

Update tests so they require:
- production nginx has no `location /api/`;
- nginx proxies `/` and `/web-api/*` through `web:4173`;
- nginx keeps source-pipeline and taxonomy-classification webhook routes;
- nginx keeps Logto host routes;
- production `api` service is not attached to the external/edge proxy path;
- `web` is attached to both `backend` and `edge`;
- `web` has Redis, Logto, and internal API env;
- env files preserve identical key set and order.

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv --directory apps/api run pytest \
  apps/api/tests/unit/core/test_prod_nginx_config.py \
  apps/api/tests/unit/core/test_compose_conventions.py \
  apps/api/tests/unit/core/test_env_file_alignment.py \
  -v
```

Expected: FAIL before infra changes.

- [ ] **Step 2: Update compose service topology**

Required changes:
- `web` joins `backend` and `edge`;
- `web` depends on `api`, `redis`, and `logto`;
- `web` receives `KNOWLEDGE_WEB_*` env values;
- remove `VITE_API_BASE_URL` and `API_PROXY_TARGET`;
- `api` remains on `backend` only for production exposure purposes;
- keep dev host port `8001:8000` for local operator diagnostics unless a separate decision removes it;
- keep web dev host port `5174:5173`.

Important: the current tracked compose filenames are `infra/compose/docker-compose.*.yml`; update those files directly.

- [ ] **Step 3: Update nginx**

Required nginx behavior:
- no public `location /api/`;
- route all public app paths to `web:4173`;
- preserve exact webhook receiver routes;
- preserve Logto public/admin host routes;
- preserve forwarded headers.

- [ ] **Step 4: Update env templates**

Add `KNOWLEDGE_WEB_*` keys in the same order to:
- `infra/env/.env.example`
- `infra/env/.env.dev`
- `infra/env/.env.prod`
- `infra/env/.env.test`

Remove `VITE_API_BASE_URL` once browser code no longer consumes it.

- [ ] **Step 5: Re-run infra tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv --directory apps/api run pytest \
  apps/api/tests/unit/core/test_prod_nginx_config.py \
  apps/api/tests/unit/core/test_compose_conventions.py \
  apps/api/tests/unit/core/test_env_file_alignment.py \
  -v
```

Expected: PASS.

- [ ] **Step 6: Controller finalizes task**

Confirm:
- public nginx no longer exposes backend FastAPI REST routes;
- web can reach `api` and `redis` over Docker DNS;
- browser runtime gets no private API origin;
- env key alignment remains green.

Commit message shape:
- `[plan:2026-04-26-web-bff-auth-access-control-plan][task:T06] make API private behind web BFF`

## Chunk 6: End-to-End Verification and Spec Freshness

### Task T07: Run full JS/infra checks and update specs only for implementation-discovered truth

**Task ID:** `T07`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify only if needed:
  - `.orbital/specs/designs/web-bff-auth-access-control.md`
  - `.orbital/specs/designs/06-deployment-docker.md`
  - related files touched by implementation reality.

- [ ] **Step 1: Run web unit tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web run test
```

Expected: PASS.

- [ ] **Step 2: Run JS typecheck and build**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm run js:typecheck
pnpm run web:build
```

Expected: PASS.

- [ ] **Step 3: Run JS lint/format check**

Run:

```bash
cd /Users/mianqin/Code/knowledge
pnpm run js:lint
```

Expected: PASS.

- [ ] **Step 4: Run infra boundary tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv --directory apps/api run pytest \
  apps/api/tests/unit/core/test_prod_nginx_config.py \
  apps/api/tests/unit/core/test_compose_conventions.py \
  apps/api/tests/unit/core/test_env_file_alignment.py \
  -v
```

Expected: PASS.

- [ ] **Step 5: Optional Docker smoke check**

When local Docker resources are available, run:

```bash
cd /Users/mianqin/Code/knowledge
docker compose \
  --env-file infra/env/.env.dev \
  -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.dev.yml \
  up --build web nginx
```

Manual smoke targets:
- `http://localhost:5174/` serves the React app through Express.
- `http://localhost:5174/web-api/auth/session` returns anonymous session JSON.
- `http://localhost:5174/api/v1/search` does not behave as a browser-supported public API route.
- Search and Graph View use `/web-api/*` in the browser network panel.

Do not claim Docker smoke success unless this command is actually run.

- [ ] **Step 6: Spec freshness pass**

Read the implementation diff against the accepted specs:
- if implementation matches specs, no spec edit is needed;
- if implementation discovers a real route/env/runtime correction, update the owning design file in the same task;
- do not document speculative MCP behavior beyond the already reserved future boundary.

- [ ] **Step 7: Controller finalizes task**

Confirm:
- all required tests/checks pass or failures are explicitly documented;
- specs remain current-truth;
- no unrelated changes were staged;
- unrelated pre-existing changes, such as `.orbital/specs/designs/taxonomy.md`, are not reverted or included unless separately requested.

Commit message shape:
- `[plan:2026-04-26-web-bff-auth-access-control-plan][task:T07] verify BFF auth access boundary`

## Coverage Gate Mapping

| Requirement / Design Rule | Tasks | Implementation Files | Verification | Spec Source |
| --- | --- | --- | --- | --- |
| Browser must not call private FastAPI directly | T04, T05, T06 | `apps/web/server/routes/*`, `apps/web/src/shared/web-api/*`, `infra/docker/nginx/default.conf` | `rg` browser scan, route tests, nginx tests | `web-bff-auth-access-control.md`, `03-architecture-constraints.md` |
| BFF owns explicit web-facing endpoints | T04 | `apps/web/server/routes/search.ts`, `apps/web/server/routes/taxonomyView.ts` | `server/routes/*.test.ts` | `web-bff-auth-access-control.md` |
| Anonymous users can use Search and Graph View under strict limits | T03, T04, T05 | `server/access/*`, `server/routes/*`, browser query adapters | quota tests, BFF route tests, web tests | `web-bff-auth-access-control.md`, `00-system-definition.md` |
| Authenticated Logto users receive higher quotas | T02, T03 | `server/auth/*`, `server/access/*` | auth route tests, quota tests | `web-bff-auth-access-control.md`, `05-technology-stack-selection.md` |
| Quotas use request-count now and reserve `cost` for future weighting | T03 | `server/access/quotaPolicy.ts`, `server/access/quotaMiddleware.ts` | quota middleware tests | `web-bff-auth-access-control.md` |
| BFF session state is server-side and browser receives httpOnly cookies only | T02, T03 | `server/auth/*`, `server/session/*`, `server/access/anonymousIdentity.ts` | auth route tests, anonymous identity tests | `web-bff-auth-access-control.md` |
| Redis is reused with separate session/quota boundaries | T02, T03, T06 | `server/session/redisSessionStore.ts`, `server/access/quotaStore.ts`, compose env | unit tests, compose tests | `06-deployment-docker.md`, `web-bff-auth-access-control.md` |
| Production exposes web/Logto/webhook only, not public FastAPI REST | T06 | `infra/docker/nginx/default.conf`, `infra/compose/docker-compose.prod.yml`, `infra/compose/docker-compose.base.yml` | nginx tests, compose tests | `06-deployment-docker.md`, `00-system-definition.md` |
| Future MCP remains out of scope but not blocked | T07 | specs only if freshness correction needed | spec freshness review | `web-bff-auth-access-control.md` |

## Final Validation Command Set

Run before claiming implementation complete:

```bash
cd /Users/mianqin/Code/knowledge
pnpm --filter web run test
pnpm run js:typecheck
pnpm run web:build
pnpm run js:lint
uv --directory apps/api run pytest \
  apps/api/tests/unit/core/test_prod_nginx_config.py \
  apps/api/tests/unit/core/test_compose_conventions.py \
  apps/api/tests/unit/core/test_env_file_alignment.py \
  -v
rg -n "VITE_API_BASE_URL|API_PROXY_TARGET|/api/v1|shared/api/contractsClient|@knowledge/contracts/generated/client" apps/web/src apps/web/vite.config.ts
```

Expected final `rg` result:
- no browser runtime matches for private backend API access;
- type-only imports from `@knowledge/contracts/generated/types` remain allowed.
