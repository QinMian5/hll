---
abstract: Frontend content-shell design for the route-addressable Graph View canvas with canonical LCC slug paths, Figma-matched desktop and mobile shell projection, and in-canvas overlays.
out_of_scope: Shared app-shell navigation, taxonomy API payload semantics, renderer-internal layout algorithms, and authentication or repository-link behavior.
---

# Design: taxonomy-view-shell

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the active content-shell, route-addressing, and layout behavior for the `Graph View` route so taxonomy browsing uses one stable canvas host inside the shared web app shell and preserves deep taxonomy position across refresh through canonical LCC slug paths.
- **Scope/Boundaries:** Covers the primary canvas container, Graph View route shape, Figma content-slot hierarchy, breadcrumb presentation, overlay placement, status presentation, and graph-route content responsiveness for `apps/web`. Excludes shared top navigation, backend graph data derivation, and auth/repository integration.
- **Related Requirements:** R-001, R-003, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Frontend behavior remains within the unified web client boundary, consumes Graph View data through BFF-owned web data adapters, preserves explicit module boundaries, and keeps behavior-changing graph-route shell decisions synchronized in active specs.
- **Detail Commitments:** The `Graph View` route renders inside the shared app shell defined by `web-app-shell-navigation.md` and owns one stable full-slot `TaxonomyCanvas` content surface. `/graph` renders the taxonomy root, and `/graph/<canonical-lcc-slug-path>` renders the branch or card scope resolved by the taxonomy-owned path endpoint, including virtual Unclassified card scopes addressed by path. Breadcrumb, loading, and error UI render as overlays inside the canvas. The host can mount the branch React Flow renderer or the card-scope deck.gl renderer without changing content-shell geometry. Graph-route content styling is expressed primarily through Tailwind utility classes instead of page-owned handwritten CSS. Approved Figma frames remain the primary source of truth for graph-route shell composition: desktop follows node `702:3845`, mobile follows node `702:3950`, and card-scope mode inherits this shell while keeping graph-internal rendering governed by `taxonomy-view-layouts.md`.
- **Update Rule:** Requirement-level repository and contract constraints remain stable while graph-route content-shell structure, overlay rules, and visual layout behavior are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Taxonomy view query states and payloads already owned by `TaxonomyViewPage`.
  - The current Graph View route path from TanStack Router: `/graph` or `/graph/<canonical-lcc-slug-path>`.
  - Shared app shell defined in `web-app-shell-navigation.md`.
  - Approved graph-route Figma frames in file `WBYs6P9HMxe21TSYQL637r`: desktop node `702:3845` and mobile node `702:3950`.
  - Accepted branch drill-down behavior and card-scope graph browsing behavior.
  - Taxonomy-owned response fields for `route_slug` and `route_path`.
- **Outputs:**
  - One graph-route content shell with one persistent full-slot taxonomy canvas.
  - One route-addressed browsing state where the active taxonomy node is restored from the URL path.
  - One Figma-matched content hierarchy where desktop uses a `320px` sidebar plus `1120px` main content region and mobile uses a `64px` header plus `440px x 892px` content region.
  - In-canvas overlays for breadcrumb, loading state, and error state.
- **Artifacts:**
  - `apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
  - `apps/web/src/index.css`

## Design Approach
- **Approach:** The `Graph View` route renders one stable `TaxonomyCanvas` host as the routed content inside the shared app shell body. That host mounts the branch React Flow renderer for root and branch states and mounts the card-scope deck.gl renderer for card-scope states. Status and navigation affordances are layered inside the canvas so layout height stays stable across root, branch, card-scope, loading, and error states. Content-shell styling is carried directly by Tailwind utility classes in the React tree, with handwritten CSS reserved only for library-level overrides or effects that cannot be expressed cleanly through utilities. Container hierarchy, edge spacing, breadcrumb placement, and branch/root atmosphere are projected from approved Figma frames before runtime-specific adjustments are introduced.
- **Key Elements:**
  - **Route state ownership:** Graph View active taxonomy position is owned by the browser route. `/graph` represents the real taxonomy root. `/graph/<canonical-lcc-slug-path>` represents a branch or card scope resolved through the BFF taxonomy path endpoint.
  - **Canonical path source:** The frontend does not derive canonical LCC paths from display labels. It uses `route_path` values returned by the taxonomy view payload for branch-node navigation and breadcrumb navigation.
  - **Path query rule:** Root route state calls the root taxonomy view endpoint. Path route state calls the path taxonomy view endpoint with the complete canonical route path from the URL.
  - **Invalid path rule:** If a path route does not resolve, the canvas shows the existing Graph View error overlay inside the stable canvas and leaves the browser path unchanged.
  - **Route body placement:** The graph canvas sits inside the shared app shell content slot and does not own a second top-level header.
  - **Desktop content slot:** Desktop composition follows the approved `1440px x 1024px` frame: the shared sidebar occupies `320px`, the main content region occupies the remaining `1120px`, and the routed `Content` frame fills the full `1120px x 1024px` region.
  - **Mobile content slot:** Mobile composition follows the approved `440px x 956px` frame: the shared mobile header is `64px` high and the routed `Content` frame fills the remaining `440px x 892px` region.
  - **Primary canvas:** The main browsing area is one persistent `TaxonomyCanvas` container that fills the routed content frame. Root and branch states mount the React Flow branch renderer. Card-scope state mounts the deck.gl graph renderer inside the same full-slot container.
  - **Canvas clipping rule:** The `TaxonomyCanvas` owns the page-level clipping boundary. Renderer wrappers and intermediate page containers keep the active scene contained to the content slot while preserving the approved branch bubble halo and label presentation within that slot.
  - **Branch bubble composition:** Branch bubbles follow the approved desktop and mobile branch frame structure: halo, surface, centered label, and size tiers projected from the Figma content components. Bubble sizing, label box sizing, and glow spread should match the Figma branch frame families rather than generic circle defaults.
  - **Card-scope shell inheritance:** Card-scope mode mounts inside the same `TaxonomyCanvas` content slot and inherits the desktop/mobile shell geometry, breadcrumb placement, and status overlay placement. Point/card internals remain governed by `taxonomy-view-layouts.md`.
  - **Breadcrumb overlay:** Breadcrumb navigation is positioned at the top-left inside the canvas as a floating overlay. Desktop uses `24px` top and left offsets. Mobile uses `20px` top and left offsets. The breadcrumb uses light inline text navigation with chevron separators and does not consume vertical layout space outside the flow scene.
  - **Loading overlay:** Pending query state renders as a centered overlay above the canvas content. The canvas frame stays visible and sized identically while the loading layer is shown.
  - **Error overlay:** Error state renders in the same overlay region as loading, preserving the same canvas geometry. The error message remains accessible with alert semantics.
  - **Card-scope layout readiness overlay:** A taxonomy `layout_not_ready` response renders a specific in-canvas preparation overlay with alert semantics and a retry action. The overlay preserves the current Graph View route and canvas geometry.
  - **Manual retry rule:** The first-version readiness overlay uses user-initiated retry. It may read the backend `Retry-After` value for retry affordance timing, but it does not aggressively auto-poll.
  - **Canvas atmosphere:** The page background and `TaxonomyCanvas` use the approved quiet `knowledge-bg-page-start` surface. Any renderer-provided grid or background treatment must remain visually subordinate to that product-shell atmosphere.
  - **No extra information panels:** The page shell excludes standalone title, subtitle, breadcrumb strip, and current-node summary cards outside the canvas.
- **Interactions:**
  - Clicking a branch node navigates to the child node's returned canonical Graph View path and keeps the user inside the same mounted canvas.
  - Clicking a breadcrumb item navigates to the selected ancestor's returned canonical Graph View path while preserving shell geometry.
  - Root state shows the breadcrumb overlay in its root form.
  - Card-scope state keeps the same shell and canvas while rendering the scope-scoped nodes in the dedicated deck.gl scene.
  - Browser back and forward navigation restore prior Graph View route paths and reload the matching root, branch, or card-scope state through the same query rules.
  - Browser refresh on a deep Graph View route restores the same active taxonomy node when the canonical route path still resolves.
  - Clicking retry on the card-scope layout readiness overlay reruns the current route query and keeps the browser path unchanged.
## Validation
- **Checks:**
  - The `Graph View` route renders one stable full-slot `TaxonomyCanvas` inside the shared app shell.
  - `/graph` renders root state through the root taxonomy view endpoint.
  - `/graph/<canonical-lcc-slug-path>` renders branch or card-scope state through the path taxonomy view endpoint.
  - Branch bubble clicks perform router navigation to returned canonical child paths.
  - Breadcrumb clicks perform router navigation to returned canonical ancestor paths.
  - Browser back and forward navigation restore earlier Graph View root, branch, and card-scope route states.
  - Refreshing a deep Graph View route restores the active branch or card scope when the taxonomy path still resolves.
  - Invalid Graph View paths render the in-canvas error state.
  - Card-scope routes that receive `layout_not_ready` render the specific in-canvas preparation overlay instead of the generic taxonomy unavailable overlay.
  - The card-scope layout readiness overlay exposes a retry action that reruns the current route query without changing the route path.
  - The card-scope layout readiness overlay does not create an aggressive auto-poll loop.
  - Desktop Graph View uses the approved `320px` sidebar plus `1120px x 1024px` routed content geometry.
  - Mobile Graph View uses the approved `64px` header plus `440px x 892px` routed content geometry.
  - Branch bubble glow, sizing, layering, and label centering match the approved desktop and mobile Graph View Figma frames.
  - Breadcrumb renders inside the canvas at top-left, uses the approved desktop and mobile offsets, and reads as inline text navigation with chevron separators.
  - Loading and error states render as overlays inside the canvas instead of replacing the page layout.
  - Canvas dimensions remain stable across root, branch, card-scope, loading, and error states.
  - Branch drill-down and ancestor-jump interactions are supported.
  - Card-scope pan, zoom, and viewport-scoped rendering stay contained inside the same shell geometry.
  - Card-scope mode inherits the approved desktop and mobile shell geometry without changing graph-internal renderer behavior.
  - Status overlays preserve current accessibility semantics for loading and error messaging.
- **Evidence:**
  - Updated page implementation and CSS reflect the shell contract in `apps/web`.
  - Frontend verification passes for the modified page.
  - Visual inspection against the approved graph-route Figma frame confirms the canvas composition.
