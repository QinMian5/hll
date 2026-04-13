---
abstract: Frontend content-shell design for the Graph View route with a stable single-canvas host, Figma-matched canvas panel styling, and in-canvas overlays.
out_of_scope: Shared app-shell navigation, taxonomy API payload semantics, renderer-internal layout algorithms, and authentication or repository-link behavior.
---

# Design: taxonomy-view-shell

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the active content-shell and layout behavior for the `Graph View` route so taxonomy browsing uses one stable canvas host inside the shared web app shell without changing the taxonomy drill-down contract.
- **Scope/Boundaries:** Covers the primary canvas container, Figma panel treatment, breadcrumb presentation, overlay placement, status presentation, and graph-route content responsiveness for `apps/web`. Excludes shared top navigation, backend payload shape, graph data derivation, and auth/repository integration.
- **Related Requirements:** R-001, R-003, R-004, R-006.

## Constraint Projection
- **Governing Constraints:** Frontend behavior remains within the unified web client boundary, consumes generated taxonomy contracts without ad hoc API access, preserves explicit module boundaries, and keeps behavior-changing graph-route shell decisions synchronized in active specs.
- **Detail Commitments:** The `Graph View` route renders inside the shared app shell defined by `web-app-shell-navigation.md` and owns one stable taxonomy canvas host wrapped by a Figma-matched panel surface. Breadcrumb, loading, and error UI render as overlays inside the canvas instead of separate page sections. The host can mount the branch React Flow renderer or the leaf deck.gl renderer without changing content-shell geometry. Graph-route content styling is expressed primarily through Tailwind utility classes instead of page-owned handwritten CSS. Approved Figma frames remain the primary source of truth for graph-route shell composition: branch view follows node `6:3`, and leaf point mode follows node `91:227`.
- **Update Rule:** Requirement-level repository and contract constraints remain stable while graph-route content-shell structure, overlay rules, and visual layout behavior are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Taxonomy view query states and payloads already owned by `TaxonomyViewPage`.
  - Shared app shell defined in `web-app-shell-navigation.md`.
  - Approved graph-route Figma frames in file `WBYs6P9HMxe21TSYQL637r`: branch node `6:3` and leaf point-mode node `91:227`.
  - Existing branch drill-down behavior and leaf graph browsing behavior.
- **Outputs:**
  - One graph-route content shell with one persistent main canvas.
  - One Figma-matched inner canvas panel with the approved border, radius, fill, and shadow treatment.
  - In-canvas overlays for breadcrumb, loading state, and error state.
- **Artifacts:**
  - `apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
  - `apps/web/src/index.css`

## Design Approach
- **Approach:** The `Graph View` route renders one stable canvas host inside the shared app shell body. That host mounts the branch React Flow renderer for root and branch states and mounts the leaf deck.gl renderer for leaf states. Status and navigation affordances are layered inside the canvas so layout height does not jump across root, branch, leaf, loading, or error states. Content-shell styling is carried directly by Tailwind utility classes in the React tree, with handwritten CSS reserved only for library-level overrides or effects that cannot be expressed cleanly through utilities. Container hierarchy, spacing, radius, border, glow containment, breadcrumb placement, and branch/leaf atmosphere should be projected from approved Figma frames before runtime-specific adjustments are introduced.
- **Key Elements:**
  - **Route body placement:** The graph canvas sits inside the shared app shell content area and does not own a second top-level header.
  - **Page spacing:** The graph-route content area uses the shared shell spacing contract so the primary canvas panel reads as a distinct surface instead of a full-bleed white work area.
  - **Primary canvas:** The main browsing area is one persistent container that hosts the active taxonomy renderer. Root and branch states mount the React Flow branch renderer. Leaf state mounts the deck.gl leaf renderer. Inside that container, the canvas content sits within a rounded panel surface that matches the approved Figma frames: `32px` corner radius, a light cool border, a soft white-to-blue gradient fill, and large low-contrast shadowing.
  - **Canvas clipping rule:** The panel surface may clip content only at the panel boundary. Renderer wrappers and intermediate page containers must not introduce extra clipping boundaries that truncate approved bubble glow, leaf edge extensions, or other Figma-matched atmosphere before the panel edge.
  - **Branch bubble composition:** Branch bubbles follow the approved branch frame structure: halo, surface, core glow, sheen, centered label, and the approved slight per-bubble rotation offsets. Bubble sizing, label box sizing, and glow spread should match the Figma branch frame families rather than generic circle defaults.
  - **Leaf point composition:** Leaf point mode follows the approved Figma point/edge hierarchy: light cool straight edges, inner and outer point sizes, and breadcrumb overlay placement inside the panel. The deck.gl renderer remains responsible for runtime rendering, but its colors, stroke widths, point radii, and shell composition should align with the approved Figma point-mode frame.
  - **Breadcrumb overlay:** Breadcrumb navigation is positioned at the top-left inside the canvas as a floating overlay. It remains inside the canvas boundary and does not consume vertical layout space outside the flow scene. The breadcrumb is rendered as light inline text navigation, not as pill or chip controls, and should avoid extra clipping wrappers beyond the panel boundary.
  - **Loading overlay:** Pending query state renders as a centered overlay above the canvas content. The canvas frame stays visible and sized identically while the loading layer is shown.
  - **Error overlay:** Error state renders in the same overlay region as loading, preserving the same canvas geometry. The error message remains accessible with alert semantics.
  - **Canvas atmosphere:** The panel surface provides the dominant visual background. Any renderer-provided grid or background treatment must remain visually subordinate to the panel fill and must not override the approved Figma atmosphere.
  - **No extra information panels:** The page shell excludes standalone title, subtitle, breadcrumb strip, and current-node summary cards outside the canvas.
- **Interactions:**
  - Clicking a branch node updates the active taxonomy node and keeps the user inside the same mounted canvas.
  - Clicking a breadcrumb item jumps to the selected ancestor while preserving shell geometry.
  - Root state shows the breadcrumb overlay in its root form.
  - Leaf state keeps the same shell and canvas while rendering the leaf-scoped nodes in the dedicated deck.gl scene.
## Validation
- **Checks:**
  - The `Graph View` route renders one stable content shell inside the shared app shell.
  - The canvas panel reads as a distinct inner surface with the approved spacing, gradient fill, border, radius, and shadow treatment.
  - Branch bubble glow is visible up to the panel boundary and is not truncated by intermediate `overflow-hidden` wrappers.
  - Branch bubble sizing, layering, label centering, and slight rotation offsets match the approved branch Figma frame families.
  - Breadcrumb renders inside the canvas at top-left, does not push down the flow scene, and reads as inline text navigation instead of chip controls.
  - Loading and error states render as overlays inside the canvas instead of replacing the page layout.
  - Canvas dimensions remain stable across root, branch, leaf, loading, and error states.
  - Branch drill-down and ancestor-jump interactions are supported.
  - Leaf pan, zoom, and viewport-scoped rendering stay contained inside the same shell geometry.
  - Leaf point mode uses the approved point sizes, line tone, and breadcrumb-in-panel composition from the Figma point-mode frame.
  - Status overlays preserve current accessibility semantics for loading and error messaging.
- **Evidence:**
  - Updated page implementation and CSS reflect the shell contract in `apps/web`.
  - Frontend verification passes for the modified page.
  - Visual inspection against the approved graph-route Figma frame confirms the canvas composition.
