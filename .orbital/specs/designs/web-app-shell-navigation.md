---
abstract: Shared frontend app shell design for the web client with Figma-first top navigation, Search route composition, and an auth action slot.
out_of_scope: Taxonomy renderer internals, backend search ranking semantics, and Logto session implementation.
---

# Design: web-app-shell-navigation

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the shared web app shell for the frontend so `Overview`, `Graph View`, and `Search` render inside one consistent top-level layout with route-driven navigation and Figma-first visual structure.
- **Scope/Boundaries:** Covers route ownership, default entry routing, shared top navigation, shared body spacing, Search page empty/results composition, and shell-level visual behavior for `apps/web`. Excludes taxonomy graph rendering rules, backend search semantics, and Logto session implementation.
- **Related Requirements:** R-001, R-003, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Frontend behavior remains within the unified web client boundary, uses BFF-owned web data adapters for browser-visible application data, preserves explicit module boundaries, and keeps behavior-changing page-structure decisions synchronized in active specs.
- **Detail Commitments:** The frontend uses one shared app shell for `Overview`, `Graph View`, and `Search`. The root route redirects to `Overview`. The shared top navigation displays `Overview`, `Graph View`, and `Search` in the center, with a left-side brand block and a right-side action group containing the icon-only `GitHub` placeholder and the auth action slot. The top navigation and Search route follow Figma file `WBYs6P9HMxe21TSYQL637r`, node `128:90`. The web client loads and uses Geist as the app-wide primary font. Shell styling is expressed primarily through Tailwind utility classes instead of page-owned handwritten CSS. Approved Figma auto-layout and grid structure is the primary source of truth for page composition; implementation should translate those structures directly instead of approximating them through unrelated wrappers, ad hoc spacing offsets, or viewport-driven compression.
- **Update Rule:** Requirements remain stable at the repository-governance layer while route ownership, shell structure, navigation state rules, and Search page presentation stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Shared browser entrypoint and route mounting in `apps/web`.
  - Approved Figma reference for shared top navigation and Search empty/results composition: file `WBYs6P9HMxe21TSYQL637r`, node `128:90`.
  - Taxonomy graph page mounted under the shared shell as the `Graph View` route.
- **Outputs:**
  - One shared shell with top navigation and body container.
  - One route set for `/overview`, `/graph`, and `/search`, with `/` redirecting to `/overview`.
  - One Search page with URL-driven empty/results state behavior.
  - One top-right action group for the `GitHub` placeholder and auth action slot.
- **Artifacts:**
  - `apps/web/src/main.tsx`
  - `apps/web/src/App.tsx`
  - `apps/web/src/app/router.tsx`
  - `apps/web/src/features/search/pages/index.tsx`
  - `apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - Additional shell-level frontend components under `apps/web/src/` when implementation begins.

## Design Approach
- **Approach:** The web client renders one shared `AppShell` that owns the top navigation and the body content container. Route resolution decides whether the shell body renders the `Overview`, `Graph View`, or `Search` page. `Search` remains a single route and uses URL query state to switch between its empty and results layouts so the page supports deep links, refresh restoration, and browser history navigation without introducing separate empty/results route branches. App-shell and Search composition are derived from approved Figma auto-layout and grid structures first, then translated into Tailwind utilities.
- **Key Elements:**
  - **Route ownership:** The frontend exposes `/overview`, `/graph`, and `/search`. The root route redirects to `/overview`.
  - **Shared shell:** Every page renders within one shell that owns the top navigation, horizontal spacing, and vertical viewport composition.
  - **Top navigation:** The shell header follows the approved Figma top-nav structure. Desktop uses a `64px` header, a `240px` brand group with a `30px` brand mark, a centered `278px` navigation group, and a `240px` right action group with a `40px` icon-only GitHub placeholder and a `92px` auth action button. Mobile uses a `112px` two-row header with a `170px` brand group, `124px` right action group, and centered `300px` navigation group. Navigation highlight is route-driven: the active item uses darker text and a bottom underline, and inactive items use one consistent muted gray treatment.
  - **Overview route:** `Overview` renders as a true page route inside the shared shell. The first version is a placeholder page and does not define future Overview feature structure beyond that route-owned placeholder state.
  - **Graph View route:** `Graph View` renders the taxonomy browsing experience inside the shared shell body. Graph-specific layout rules remain governed by taxonomy design documents.
  - **Search route:** `Search` renders a Figma-aligned page rather than a graph canvas. It supports two states within one route:
    - **Empty state:** A large centered search bar sits within a quiet, high-whitespace content surface.
    - **Results state:** The page shows a top search bar row, a left-side results grid, and a right-side suggestions panel.
  - **Projection rule:** The Search route is projected from the approved desktop and mobile Figma frames as responsive layout structure rather than fixed viewport reproduction. Desktop uses the `1440x1024` frame as the visual reference, but implementation must preserve grid proportions, fill sizing, and minimum-content safety across narrower desktop widths. Mobile uses the `440x956` frame proportions with a stacked routed body under the mobile header.
  - **Search bar structure:** The search bar follows the approved component hierarchy. Desktop uses `760x64`, `22px` left padding, `10px` right padding, `16px` radius, a dedicated `44x44` icon-button container, and a `20x20` search icon centered inside that container. Mobile uses full available width, `56px` height, `18px` left padding, `8px` right padding, a `40x40` icon-button container, and an `18x18` search icon.
  - **Search results structure:** Results stay stacked below the large breakpoint so medium-width screens can use the available width for the results grid instead of squeezing a sidebar. From the large breakpoint upward, results use the approved Figma `ResultsContent / Responsive Grid` structure with a left results track and right suggestions track. The large breakpoint uses a `2fr / 1fr` split because the results grid is limited to two card columns at that width. The extra-large breakpoint uses a `3fr / 1fr` split because the results grid expands to three card columns. The right suggestions panel must be a grid track participant with fill sizing, not a fixed-width sidebar. The results card list uses explicit responsive column counts that preserve one column on mobile, two result columns on small through large widths, and three result columns only at extra-large widths and above. Mobile and medium results use a stacked content area with suggestions below the results list. Results lists, suggestions lists, and card bodies use content-driven overflow containers; visible scrollbar chrome is not a fixed design element and must not be represented by hardcoded decorative bars in implementation. Cards and suggestions inherit their radius, border, shadow, and typography from the approved Figma structures rather than from generic shared surface defaults.
  - **Search card text rule:** Search result card `title` and `content` render through the shared knowledge-card rich-text contract defined in `web-knowledge-card-rich-text.md`.
  - **Search state ownership:** Search state is URL-addressable. The absence of an effective query renders the empty state. The presence of a query renders the results layout.
  - **Visual language:** The shared shell uses a restrained product-shell style: Geist typography, light header, subtle divider, large whitespace, quiet surfaces, and no extra decorative chrome beyond the approved Figma direction.
  - **Tailwind-first implementation rule:** Shared shell layout, navigation presentation, and Search page presentation are carried primarily through Tailwind utility classes colocated with the React tree. Handwritten CSS is reserved only for library-level overrides or effects that cannot be expressed cleanly through utilities.
- **Interactions:**
  - Navigating between `Overview`, `Graph View`, and `Search` uses route changes rather than local tab state.
  - Browser refresh and deep linking preserve the active route.
  - Search query updates preserve the `/search` route and change only URL query state plus in-page layout state.
  - The `GitHub` placeholder does not trigger navigation or mutation.
  - The auth action slot renders login/session actions defined by `web-bff-auth-access-control.md`.

## Validation
- **Checks:**
  - The frontend uses one shared shell for `Overview`, `Graph View`, and `Search`.
  - Visiting `/` lands on `/overview`.
  - The top navigation contains `Overview`, `Graph View`, and `Search`, with only the active route highlighted.
  - The top navigation uses the approved Figma header sizing, typography, action sizing, and centered three-column nav structure.
  - The web client uses Geist as the app-wide primary font.
  - `Overview` exists as a true routed placeholder page.
  - `Graph View` renders within the shared shell rather than owning a separate top-level header.
  - `Search` uses one route with URL-driven empty/results state switching instead of separate routes for each visual state.
  - The Search empty state matches the approved single centered search-bar composition.
  - The Search results state matches the approved top search row plus left results grid plus right suggestions layout.
  - The Search results state uses responsive grid proportions and card vertical rhythm derived from the approved desktop and mobile Figma frames without fixed desktop sidebar or card widths that can force horizontal overflow.
  - Search results, suggestions, and card-body scrolling are controlled by content overflow rather than static scrollbar decoration.
  - Search result card `title` and `content` use the shared knowledge-card rich-text renderer instead of raw string rendering.
  - The Search icon is centered inside the approved `44x44` icon-button container rather than positioned through ad hoc offset utilities.
  - Shell-level styling is carried primarily by Tailwind utilities rather than large handwritten CSS blocks.
- **Evidence:**
  - Updated frontend route and page-shell implementation in `apps/web` reflects the shared shell contract.
  - Frontend verification covers route mounting, active-nav state, and Search empty/results rendering.
  - Visual inspection confirms alignment with the approved Figma page structure.
