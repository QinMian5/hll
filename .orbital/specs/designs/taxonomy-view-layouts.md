---
abstract: Frontend layout and visual-language design for branch and leaf taxonomy views inside the single React Flow canvas.
out_of_scope: Taxonomy API payload semantics, page-shell chrome structure, and repository-link or authentication behavior.
---

# Design: taxonomy-view-layouts

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted layout behavior and bubble visual language for branch and leaf browsing inside the taxonomy page canvas so branch navigation and leaf relation reading each use fit-for-purpose geometry while sharing the approved Figma presentation.
- **Scope/Boundaries:** Covers branch bubble sizing and placement, leaf graph level-of-detail behavior, Figma-aligned bubble composition, hover-content behavior, typography, Tailwind-first styling boundaries, viewport-driven hydration, and layout-stability rules for `apps/web`. Excludes taxonomy payload ownership, page-shell header and overlay structure, and backend graph semantics beyond the consumed skeleton/detail contracts.
- **Related Requirements:** R-001, R-003, R-004, R-006.

## Constraint Projection
- **Governing Constraints:** Frontend behavior stays within the unified web client, consumes generated taxonomy contracts without ad hoc HTTP access, preserves explicit module boundaries, and keeps behavior-changing layout decisions synchronized in active specs.
- **Detail Commitments:** Branch and leaf views use separate layout pipelines inside the same React Flow canvas. Branch layout is a weighted floating bubble field derived from the current layer's taxonomy children. Leaf layout is a two-stage one-hop relation browser: point-mode skeleton first, then viewport-scoped bubble hydration after zoom activation. Branch and hydrated leaf nodes share one Figma-aligned bubble visual family, and page-owned styling is expressed primarily through Tailwind utility classes.
- **Update Rule:** Requirements remain stable at the repository-governance layer while branch and leaf layout rules, geometry constraints, and interaction-facing visual behavior are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Root and branch `children[]` payloads from taxonomy view queries.
  - Leaf skeleton `nodes[]` and `edges[]` payloads from taxonomy view queries.
  - Leaf detail batches containing `title` and `content` for explicit node ids.
  - Approved Figma reference for branch bubble composition: file `WBYs6P9HMxe21TSYQL637r`, node `6:3`.
  - Existing single-canvas page shell defined in `taxonomy-view-shell.md`.
- **Outputs:**
  - One branch-specific node layout result for current-layer taxonomy bubbles.
  - One leaf-specific point/bubble presentation result for one-hop relation browsing.
  - One shared bubble presentation system for branch and leaf nodes that aligns with Figma file `WBYs6P9HMxe21TSYQL637r`, node `6:3`.
  - Stable geometry rules that can be projected into `TaxonomyViewPage.tsx` and supporting layout helpers.
- **Artifacts:**
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/index.css`
  - Supporting frontend layout helpers under `apps/web/src/features/taxonomy-view/` when implementation begins.

## Design Approach
- **Approach:** Use two dedicated client-owned layout pipelines inside the shared React Flow canvas. Branch layout prioritizes weighted category browsing and visual breathing room over explicit edge rendering. Leaf layout prioritizes relation readability and interaction performance through level-of-detail rendering: skeleton points by default, viewport-scoped bubble hydration only after zoom activation, and node content available through hover instead of default canvas occupancy. Both pipelines project into one shared Figma-aligned bubble component family instead of separate branch-card and leaf-node visual systems.
- **Key Elements:**
  - **Branch view role:** Branch view is a floating bubble navigator for the current taxonomy level. It is not a tree diagram and does not render hierarchy edges.
  - **Branch size encoding:** Each branch bubble radius is derived from `descendant_card_count` using logarithmic scaling so large branches read as more important without overwhelming the canvas.
  - **Branch layout family:** Branch layout uses a seeded radial force pipeline. A deterministic center-out seed initializes bubble positions, then a short static `d3-force` solve applies collision avoidance, weak centering, and weak radial cohesion. The solve freezes after layout settles; the branch view does not run continuous physics.
  - **Branch spatial rule:** Larger bubbles preferentially occupy the central zone while smaller bubbles settle farther outward. The final composition should preserve open space and resemble the approved Figma bubble field rather than a tightly packed chart or a hierarchical flow diagram.
  - **Branch bubble composition:** Branch nodes are rendered as Figma-style bubbles rather than plain circular cards. The composition includes a soft halo, a pale cool surface, a restrained core glow, a light sheen layer, and centered label typography. The branch node surface does not show auxiliary affordance copy such as `Open`.
  - **Branch typography rule:** Branch labels use the approved bubble typography direction: medium-weight, tightly centered, visually compact line-height, restrained negative tracking, and size scaling that stays legible across varying bubble diameters.
  - **Leaf view role:** Leaf view is a one-hop relation graph browser. It renders the returned `nodes[]` and `edges[]` payload together and uses geometric structure to expose relational proximity rather than taxonomy hierarchy.
  - **Leaf level-of-detail rule:** Leaf view has two rendering modes. Point mode is the default whole-graph overview and uses lightweight data points with no titles or content. Bubble mode is activated only after the approved zoom threshold and only for nodes inside the active viewport plus overscan.
  - **Leaf skeleton rule:** Entering a leaf renders the full one-hop skeleton graph as points and edges without requesting or displaying node `title` or `content`.
  - **Leaf hydration rule:** Bubble mode is driven by viewport-scoped detail hydration. The frontend requests `title` and `content` only for node ids inside the current viewport plus one overscan ring, then upgrades those nodes from points to bubbles.
  - **Leaf cache rule:** Hydrated node details are cached by node id for the active leaf view and reused during subsequent pans or zooms instead of being re-requested on every movement.
  - **Leaf hydration latency rule:** Viewport-scoped hydration assumes the backend detail path validates membership and fetches details only for requested node ids. The frontend design does not depend on a backend implementation that reloads full assignment sets or full node-detail sets on every hydration request.
  - **Leaf presentation rule:** Hydrated leaf nodes render title-first. `content` does not occupy default canvas space and appears only in hover disclosure.
  - **Leaf scope handling:** `inner` and `outer` remain valid semantic markers for styling and interaction, but they do not impose geometry rules in the layout solve.
  - **Leaf layout family:** Leaf layout uses a static `d3-force` graph solve with link force, collision force, many-body separation, and weak centering. The solve runs when the leaf payload changes and then freezes to preserve spatial stability.
  - **Shared visual family rule:** Leaf nodes use the same bubble-family material language as branch nodes. Leaf presentation may be slightly calmer than branch presentation, but it remains recognizably part of the same visual system rather than switching to flat cards or generic graph chips.
  - **Leaf scope styling rule:** `inner` and `outer` can differ only through restrained variations such as glow intensity, label tone, or surface emphasis. They do not become separate component families.
  - **Hover disclosure rule:** Leaf `content` is revealed through a lightweight floating disclosure that visually belongs to the canvas and bubble system. The disclosure remains outside the default node footprint and does not use a generic dark tooltip treatment.
  - **Zoom activation rule:** Bubble hydration is gated by one explicit zoom threshold. Below the threshold, all leaf nodes remain in point mode and no title/content detail requests are sent.
  - **Viewport rule:** When bubble mode is active, only nodes inside the viewport plus overscan may render as bubbles. Nodes outside that region remain points even if their details are already cached.
  - **Movement rule:** Panning or viewport changes trigger incremental detail hydration only for newly entered overscan nodes. Already hydrated nodes reuse cache entries.
  - **Tailwind-first implementation rule:** Bubble composition, spacing, typography, and disclosure styling are carried primarily through Tailwind utility classes colocated with the React structure. Handwritten CSS is reserved only for library overrides or visual effects that cannot be expressed cleanly through utilities.
  - **Determinism rule:** Both layout pipelines use deterministic seed ordering so revisiting the same payload yields approximately stable geometry instead of visually unrelated positions.
  - **Shared canvas rule:** Branch and leaf layouts project into the same stable canvas shell. Layout changes must not change the outer shell height or the breadcrumb/loading/error overlay contract.
- **Interactions:**
  - Entering a branch view computes only the branch bubble layout for the current `children[]`.
  - Clicking a branch bubble transitions to the next taxonomy payload and recomputes the corresponding branch or leaf layout inside the same mounted canvas.
  - Entering a leaf view computes the one-hop layout from the returned skeleton payload and renders all nodes in point mode.
  - Crossing the bubble-activation zoom threshold computes the active viewport plus overscan set and hydrates leaf node details only for that region.
  - Panning inside bubble mode incrementally hydrates newly entered overscan nodes while leaving far-away nodes in point mode.
  - Hovering a hydrated leaf bubble reveals its `content` without changing the underlying graph geometry.
  - Breadcrumb jumps discard the current layout result and compute the selected ancestor state using the same deterministic layout rules.

## Validation
- **Checks:**
  - Branch view displays weighted bubbles with logarithmic size scaling and no hierarchy edges.
  - Branch composition reads as a center-out floating field with visible breathing room and no persistent overlap.
  - Branch and leaf nodes read as the same Figma-aligned bubble family rather than separate card and graph-node systems.
  - Branch bubbles do not display auxiliary affordance text such as `Open`.
  - Branch and leaf views no longer share one generic radial layout function.
  - Leaf view renders the skeleton graph from the one-hop payload without loading titles or content on entry.
  - Leaf view displays nodes as points below the zoom threshold and upgrades only viewport-scoped hydrated nodes into bubbles above the threshold.
  - Leaf node details are requested only for the viewport plus overscan region and are reused from cache during continued navigation.
  - Viewport-scoped leaf hydration remains responsive because detail requests are bounded to the requested node ids and do not trigger whole-graph detail reads on the backend.
  - Hydrated leaf nodes display only titles by default and reveal `content` on hover.
  - Breadcrumb, bubble typography, and disclosure styling remain visually aligned with the approved Figma direction.
  - Page-owned layout styling is carried primarily by Tailwind utility classes rather than large handwritten CSS blocks.
  - Leaf layout uses relation-driven geometry without forcing `inner` and `outer` into separate positional rings.
  - Re-entering the same payload yields approximately stable node positions rather than large random jumps.
  - Layout updates preserve the single-canvas shell geometry defined in `taxonomy-view-shell.md`.
- **Evidence:**
  - Updated frontend design and implementation artifacts in `apps/web` reflect the branch and leaf layout contracts.
  - Focused frontend verification covers branch drill-down, leaf point-mode entry, viewport-scoped leaf hydration, and hover disclosure behavior.
  - Browser-level visual inspection confirms branch composition matches the approved Figma direction and leaf graph remains readable as points at overview scale and as hydrated bubbles at local scale inside the stable shell.
