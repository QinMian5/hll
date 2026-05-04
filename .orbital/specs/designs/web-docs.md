---
abstract: Web Docs route for MCP client setup guidance across Codex, Claude Code, and OpenClaw.
out_of_scope: Markdown authoring pipelines, documentation search indexing, CMS storage, live token generation, and external MCP client execution.
---

# Design: web-docs

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Provide one first-class Docs route inside the shared web app shell so MCP client setup for Knowledge has a stable product-owned home.
- **Scope/Boundaries:** Covers the `/docs` route, first-version MCP client setup UI, environment-specific MCP public endpoint display, Codex setup, Claude Code setup, OpenClaw setup, and the responsive page structure projected from Figma. Excludes markdown loading, docs search, content versioning, generated client-specific secrets, and runtime validation of external client configuration.
- **Related Requirements:** R-001, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Documentation is part of the public web client boundary, must preserve clear page/module responsibility, and must keep behavior-changing navigation and page-structure decisions synchronized with active specs.
- **Detail Commitments:** The web client exposes `/docs` as a routed page inside the shared app shell. `Docs` is a primary navigation item alongside `Overview`, `Graph View`, and `Search`. The current Docs page is an MCP client setup surface titled `MCP Client Setup`, with a `Clients` selector and a selected-client `Configuration` panel. The first-version clients are `Codex`, `Claude Code`, and `OpenClaw`. Selecting one client shows only that client's setup steps. Dashboard remains the authenticated token and quota management surface. Docs owns canonical explanatory guidance for connecting external clients to the environment-specific MCP public endpoint supplied by the Web BFF. The Web BFF owns `KNOWLEDGE_WEB_MCP_PUBLIC_BASE_URL` as a first-class public configuration value; development uses `http://localhost:8002/mcp`, and production uses `https://knowledge.orbitalis.org/mcp`.
- **Update Rule:** Repository-level requirements remain stable while Docs route ownership, information architecture, page content structure, and navigation placement stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Browser route navigation to `/docs`.
  - MCP client setup templates embedded in the first-version web client.
  - Browser runtime configuration injected by the Web BFF with `mcpPublicBaseUrl`.
  - Figma-projected layout and visual assets for Codex, Claude Code, and OpenClaw client rows.
- **Outputs:**
  - A Docs page rendered inside the shared app shell.
  - A visible primary navigation entry for `Docs`.
  - Environment-specific setup commands for Codex, Claude Code, and OpenClaw.
  - Interactive client selection that updates the visible configuration panel without changing routes.
- **Artifacts:**
  - `apps/web/src/app/AppShell.tsx`
  - `apps/web/src/app/router.tsx`
  - `apps/web/server/app.ts`
  - `apps/web/server/browserRuntimeConfig.ts`
  - `apps/web/server/config.ts`
  - `apps/web/server/testSupport/webServerEnv.ts`
  - `apps/web/src/shared/config/index.ts`
  - `apps/web/src/features/docs/pages/index.tsx`
  - `apps/web/src/features/docs/pages/DocsPage.test.tsx`
  - `apps/web/src/app/AppShell.test.tsx`
  - `apps/web/src/app/bundleBoundaries.test.ts`
  - `infra/env/.env.example`
  - `infra/env/.env.dev`
  - `infra/env/.env.prod`
  - `infra/env/.env.test`
  - `infra/compose/docker-compose.base.yml`

## Design Approach
- **Approach:** Docs is a product route, not an account submenu item. It uses the existing shared shell and restrained Knowledge visual language, with a static client selector plus selected-client setup panel before a markdown or search-backed docs system exists.
- **Key Elements:**
  - **Route ownership:** `/docs` is a top-level route lazy-loaded through the app router.
  - **Primary navigation:** The shared shell renders `Docs` as an enabled primary navigation item with the same row height, spacing, active state, and drawer behavior as the existing primary routes.
  - **Page structure:** The Docs page uses an available-height routed body with a compact page header, a `Clients` rail, and a selected-client configuration detail region. The page header uses the shared routed-page header tokens defined by the app shell: `layout/page/header-height`, `typography/page/title/font-size`, and `typography/page/title/line-height`.
  - **Desktop layout:** The workspace stays stacked below `lg`. From `lg` upward it switches to two columns with a responsive client rail that follows the App Shell stepped-width rhythm: `256px` at `lg`, `288px` at `xl`, and `320px` at `2xl`. The configuration region fills the remaining width, with `16px` gaps and internal scroll areas.
  - **Mobile layout:** The same DOM and content stack vertically. The workspace uses a one-column, two-row grid with `1fr` for the client region and `2fr` for the configuration region, so the split follows the available Docs workspace height instead of fixed pixel heights.
  - **Client setup taxonomy:** `Codex`, `Claude Code`, and `OpenClaw` are first-version client pages inside the selector. Each client contains three ordered setup steps, command blocks, and copy controls. Only the selected client's steps are visible.
  - **MCP endpoint source:** The Docs page reads `mcpPublicBaseUrl` from browser runtime configuration injected by the Web BFF. The browser-visible value comes from the Web BFF's `KNOWLEDGE_WEB_MCP_PUBLIC_BASE_URL` setting and represents the public MCP endpoint that external clients should use.
  - **Public runtime configuration:** Browser runtime configuration exposes only public client-facing values needed by browser UI. Internal API origins, MCP internal usage-summary origins, service credentials, token URLs, and raw personal access tokens remain server-only.
  - **Command generation:** Codex, Claude Code, and OpenClaw command strings are generated from the configured MCP public endpoint at render time, so copy controls and visible command text stay aligned.
  - **Command typography:** Command blocks use the Docs terminal visual tokens and render command text in a monospace font.
  - **Scrolling behavior:** The client list and setup steps use the shared shadcn-style `ScrollArea`; the configuration title and panel header do not scroll.
  - **Dashboard boundary:** Dashboard remains the place to create, inspect, copy, rename, and delete personal access tokens. Docs remains the place to explain what those tokens are for and how external clients should be configured.
  - **Visual language:** The route follows the existing light product-shell style: Geist typography, neutral page background, white bordered panels, `8px` radii, restrained blue emphasis, Lucide copy icons, and product-client icons imported from Figma assets. Docs page title sizing follows the shared routed-page title tokens rather than Docs-local display sizing. Docs-specific page background, panel heading sizes, copy controls, scrollbars, terminal chrome, client rows, and step badges are represented with theme tokens rather than ad hoc arbitrary utilities.
- **Interactions:**
  - Navigating to `Docs` changes the route to `/docs` and highlights only the Docs primary navigation item.
  - The Web BFF serves HTML with browser runtime configuration containing the current environment's MCP public endpoint.
  - On mobile, selecting `Docs` from the drawer closes the drawer through the same route-navigation behavior as other primary routes.
  - Selecting `Codex`, `Claude Code`, or `OpenClaw` updates the configuration title, panel title, and visible setup steps in place.
  - Copy controls copy the command text containing the configured MCP public endpoint and do not display toast or bubble UI in the first version.
  - Docs content is static in the first version and does not call backend APIs.

## Validation
- **Checks:**
  - App shell tests verify `Docs` is present in desktop navigation and mobile drawer navigation.
  - Router bundle-boundary tests verify the Docs route is lazy-loaded and not imported eagerly.
  - Web server config tests verify `KNOWLEDGE_WEB_MCP_PUBLIC_BASE_URL` is required and parsed as a public URL.
  - Web app tests verify production and development HTML fallbacks include browser runtime configuration with `mcpPublicBaseUrl`.
  - Browser runtime config tests verify `mcpPublicBaseUrl` is accepted while private API and internal MCP service origins are not exposed.
  - Docs page tests verify the `MCP Client Setup` layout, `Clients` and selected-client `Configuration` headings, responsive workspace classes, shared scroll areas, Codex default content, Claude Code switching, OpenClaw switching, copy controls, configured MCP endpoint command generation, and monospace command rendering.
  - Visual inspection confirms the Docs page header uses the shared routed-page header height and title typography tokens.
  - Typecheck and frontend checks verify the route and page compile with the current React/Tailwind stack.
- **Evidence:**
  - `/docs` renders inside the shared app shell.
  - The primary navigation contains `Overview`, `Graph View`, `Search`, and `Docs`.
  - Dashboard token-management behavior remains owned by Dashboard.
  - The Docs page renders Codex, Claude Code, and OpenClaw setup content using the MCP public endpoint configured for the current environment without calling backend APIs.
