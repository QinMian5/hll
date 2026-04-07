---
abstract: Frontend shell design for the taxonomy drill-down page with a Figma-aligned header, stable single-canvas layout, and in-canvas overlays.
out_of_scope: Taxonomy API payload semantics, React Flow node layout algorithms, and authentication or repository-link behavior.
---

# Design: taxonomy-view-shell

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the active shell and layout behavior for the web taxonomy browsing page so the frontend applies the approved Figma structure without changing the taxonomy drill-down contract.
- **Scope/Boundaries:** Covers the page-level header, primary canvas container, overlay placement, status presentation, and shell-level responsiveness for `apps/web`. Excludes backend payload shape, graph data derivation, and auth/repository integration.
- **Related Requirements:** R-001, R-003, R-004, R-006.

## Constraint Projection
- **Governing Constraints:** Frontend behavior remains within the unified web client boundary, consumes generated taxonomy contracts without ad hoc API access, preserves explicit module boundaries, and keeps behavior-changing page-shell decisions synchronized in active specs.
- **Detail Commitments:** The taxonomy browsing page uses a Figma-aligned top header plus one stable React Flow canvas. Breadcrumb, loading, and error UI render as overlays inside the canvas instead of separate page sections. Header action buttons remain present but disabled until real destinations exist.
- **Update Rule:** Requirement-level repository and contract constraints remain stable while page-shell structure, overlay rules, and visual layout behavior are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Taxonomy view query states and payloads already owned by `TaxonomyViewPage`.
  - Approved Figma frame `WBYs6P9HMxe21TSYQL637r`, node `1:3`.
  - Existing React Flow rendering and node click drill-down behavior.
- **Outputs:**
  - One page shell with a fixed header and one persistent main canvas.
  - In-canvas overlays for breadcrumb, loading state, and error state.
  - Disabled top-right placeholder actions for `GitHub` and `Login`.
- **Artifacts:**
  - `apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `apps/web/src/index.css`

## Design Approach
- **Approach:** Keep the existing taxonomy drill-down logic and React Flow scene, but replace the page chrome with the approved minimal shell. The page always renders a single stable canvas area beneath a Figma-aligned header. Status and navigation affordances are layered inside the canvas so layout height does not jump across root, branch, leaf, loading, or error states.
- **Key Elements:**
  - **Header shell:** A single horizontal header spans the page width. The left side contains a blue square placeholder icon and the `Knowledge Graph` brand label. The center stays empty. The right side contains `GitHub` and `Login` buttons styled like the approved Figma buttons and marked disabled.
  - **Primary canvas:** The main browsing area is one persistent container that hosts React Flow for root, branch, and leaf browsing. The container keeps a stable height and remains mounted across query-state transitions.
  - **Breadcrumb overlay:** Breadcrumb navigation is positioned at the top-left inside the canvas as a floating overlay. It remains inside the canvas boundary and does not consume vertical layout space outside the flow scene.
  - **Loading overlay:** Pending query state renders as a centered overlay above the canvas content. The canvas frame stays visible and sized identically while the loading layer is shown.
  - **Error overlay:** Error state renders in the same overlay region as loading, preserving the same canvas geometry. The error message remains accessible with alert semantics.
  - **Default flow background:** The canvas keeps the current React Flow default grid-style background. The gray Figma fill is treated as placeholder framing and is not implemented as an additional background layer in this round.
  - **No extra information panels:** The page shell excludes standalone title, subtitle, breadcrumb strip, and current-node summary cards outside the canvas.
- **Interactions:**
  - Clicking a branch node updates the active taxonomy node and keeps the user inside the same mounted canvas.
  - Clicking a breadcrumb item jumps to the selected ancestor while preserving shell geometry.
  - Root state shows the breadcrumb overlay in its root form.
  - Leaf state keeps the same shell and canvas while rendering the leaf-scoped nodes in React Flow.
  - Disabled header buttons do not trigger navigation, mutation, or placeholder route changes.

## Validation
- **Checks:**
  - The page renders exactly two top-level visual regions: header and main canvas.
  - The header matches the approved Figma structure: left brand, empty middle area, two disabled right-side buttons.
  - Breadcrumb renders inside the canvas at top-left and does not push down the flow scene.
  - Loading and error states render as overlays inside the canvas instead of replacing the page layout.
  - Canvas dimensions remain stable across root, branch, leaf, loading, and error states.
  - React Flow drill-down and ancestor-jump interactions continue to work.
  - Shell elements provide visible disabled/focus treatment and preserve current accessibility semantics for status messaging.
- **Evidence:**
  - Updated page implementation and CSS reflect the shell contract in `apps/web`.
  - Frontend verification passes for the modified page.
  - Visual inspection against the approved Figma frame confirms the header-and-canvas composition.
