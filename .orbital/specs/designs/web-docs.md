---
abstract: Unified web documentation hub for project overview, MCP access concepts, and model-client configuration guidance.
out_of_scope: Markdown authoring pipelines, documentation search indexing, CMS storage, live token generation, and external MCP client execution.
---

# Design: web-docs

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Provide one first-class Docs route inside the shared web app shell so project explanation, MCP access guidance, Codex setup, and Claude Code setup have a stable product-owned home.
- **Scope/Boundaries:** Covers the `/docs` route, static first-version documentation information architecture, client-configuration entry points, and relationship to Dashboard token management. Excludes markdown loading, docs search, content versioning, generated client-specific secrets, and runtime validation of external client configuration.
- **Related Requirements:** R-001, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Documentation is part of the public web client boundary, must preserve clear page/module responsibility, and must keep behavior-changing navigation and page-structure decisions synchronized with active specs.
- **Detail Commitments:** The web client exposes `/docs` as a routed page inside the shared app shell. `Docs` is a primary navigation item alongside `Overview`, `Graph View`, and `Search`. The first version is a static documentation hub with `Start here` and `Client configuration` sections. `Start here` contains `Project overview`, `MCP access`, and `Security and quota`. `Client configuration` contains `Codex` and `Claude Code`. Dashboard remains the authenticated token and quota management surface; Docs owns canonical explanatory guidance and links conceptually to Dashboard as the place where users create personal tokens.
- **Update Rule:** Repository-level requirements remain stable while Docs route ownership, information architecture, page content structure, and navigation placement stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Browser route navigation to `/docs`.
  - Static documentation content embedded in the first-version web client.
  - Dashboard-owned token-management flow as the source for personal access token creation.
- **Outputs:**
  - A Docs page rendered inside the shared app shell.
  - A visible primary navigation entry for `Docs`.
  - Static guidance cards for project orientation, MCP access, security/quota, Codex configuration, and Claude Code configuration.
- **Artifacts:**
  - `apps/web/src/app/AppShell.tsx`
  - `apps/web/src/app/router.tsx`
  - `apps/web/src/features/docs/pages/index.tsx`
  - `apps/web/src/features/docs/pages/DocsPage.test.tsx`
  - `apps/web/src/app/AppShell.test.tsx`
  - `apps/web/src/app/bundleBoundaries.test.ts`

## Design Approach
- **Approach:** Docs is a product route, not an account submenu item. It uses the existing shared shell and restrained Knowledge visual language, with static cards that establish the documentation taxonomy before a markdown or search-backed docs system exists.
- **Key Elements:**
  - **Route ownership:** `/docs` is a top-level route lazy-loaded through the app router.
  - **Primary navigation:** The shared shell renders `Docs` as an enabled primary navigation item with the same row height, spacing, active state, and drawer behavior as the existing primary routes.
  - **Page structure:** The Docs page uses a scrollable routed body with a compact page header, `Start here` section, and `Client configuration` section.
  - **Start here taxonomy:** `Project overview` explains the product and surfaces, `MCP access` explains model-client access, and `Security and quota` explains token/quota concepts at a high level.
  - **Client setup taxonomy:** `Codex` and `Claude Code` are first-version client setup cards. They provide direction without persisting personal token values or exposing generated secrets.
  - **Dashboard boundary:** Dashboard remains the place to create, inspect, copy, rename, and delete personal access tokens. Docs remains the place to explain what those tokens are for and how external clients should be configured.
  - **Visual language:** The route follows the existing light product-shell style: Geist typography, neutral page background, white bordered item cards, `8px` radii, restrained blue emphasis, and no decorative imagery.
- **Interactions:**
  - Navigating to `Docs` changes the route to `/docs` and highlights only the Docs primary navigation item.
  - On mobile, selecting `Docs` from the drawer closes the drawer through the same route-navigation behavior as other primary routes.
  - Docs content is static in the first version and does not call backend APIs.

## Validation
- **Checks:**
  - App shell tests verify `Docs` is present in desktop navigation and mobile drawer navigation.
  - Router bundle-boundary tests verify the Docs route is lazy-loaded and not imported eagerly.
  - Docs page tests verify the unified documentation hub renders `Start here`, `Project overview`, `MCP access`, `Client configuration`, `Codex`, and `Claude Code`.
  - Typecheck and frontend checks verify the route and page compile with the current React/Tailwind stack.
- **Evidence:**
  - `/docs` renders inside the shared app shell.
  - The primary navigation contains `Overview`, `Graph View`, `Search`, and `Docs`.
  - Dashboard token-management behavior remains owned by Dashboard.
