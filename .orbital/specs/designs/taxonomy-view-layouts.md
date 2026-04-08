---
abstract: Frontend layout design for branch and leaf taxonomy views inside the single React Flow canvas.
out_of_scope: Taxonomy API payload semantics, page-shell chrome structure, and repository-link or authentication behavior.
---

# Design: taxonomy-view-layouts

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted layout behavior for branch and leaf browsing inside the taxonomy page canvas so branch navigation and leaf relation reading each use fit-for-purpose geometry instead of sharing one generic radial layout.
- **Scope/Boundaries:** Covers branch bubble sizing and placement, leaf graph node and edge layout, hover-content behavior, and layout-stability rules for `apps/web`. Excludes taxonomy payload ownership, page-shell header and overlay structure, and backend graph semantics.
- **Related Requirements:** R-001, R-003, R-004, R-006.

## Constraint Projection
- **Governing Constraints:** Frontend behavior stays within the unified web client, consumes generated taxonomy contracts without ad hoc HTTP access, preserves explicit module boundaries, and keeps behavior-changing layout decisions synchronized in active specs.
- **Detail Commitments:** Branch and leaf views use separate layout pipelines inside the same React Flow canvas. Branch layout is a weighted floating bubble field derived from the current layer's taxonomy children. Leaf layout is a static one-hop relation graph rendered from nodes and edges, with all nodes title-first and content revealed on hover.
- **Update Rule:** Requirements remain stable at the repository-governance layer while branch and leaf layout rules, geometry constraints, and interaction-facing visual behavior are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Root and branch `children[]` payloads from taxonomy view queries.
  - Leaf `nodes[]` and `edges[]` payloads from taxonomy view queries.
  - Approved Figma reference for branch bubble composition: file `WBYs6P9HMxe21TSYQL637r`, node `6:3`.
  - Existing single-canvas page shell defined in `taxonomy-view-shell.md`.
- **Outputs:**
  - One branch-specific node layout result for current-layer taxonomy bubbles.
  - One leaf-specific node and edge layout result for one-hop relation browsing.
  - Stable geometry rules that can be projected into `TaxonomyViewPage.tsx` and supporting layout helpers.
- **Artifacts:**
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/index.css`
  - Supporting frontend layout helpers under `apps/web/src/features/taxonomy-view/` when implementation begins.

## Design Approach
- **Approach:** Use two dedicated client-owned layout pipelines inside the shared React Flow canvas. Branch layout prioritizes weighted category browsing and visual breathing room over explicit edge rendering. Leaf layout prioritizes relation readability and node-title scanning over card-density, with node content available through hover instead of default canvas occupancy.
- **Key Elements:**
  - **Branch view role:** Branch view is a floating bubble navigator for the current taxonomy level. It is not a tree diagram and does not render hierarchy edges.
  - **Branch size encoding:** Each branch bubble radius is derived from `descendant_card_count` using logarithmic scaling so large branches read as more important without overwhelming the canvas.
  - **Branch layout family:** Branch layout uses a seeded radial force pipeline. A deterministic center-out seed initializes bubble positions, then a short static `d3-force` solve applies collision avoidance, weak centering, and weak radial cohesion. The solve freezes after layout settles; the branch view does not run continuous physics.
  - **Branch spatial rule:** Larger bubbles preferentially occupy the central zone while smaller bubbles settle farther outward. The final composition should preserve open space and resemble the approved Figma bubble field rather than a tightly packed chart or a hierarchical flow diagram.
  - **Leaf view role:** Leaf view is a one-hop relation graph browser. It renders the returned `nodes[]` and `edges[]` payload together and uses geometric structure to expose relational proximity rather than taxonomy hierarchy.
  - **Leaf node density rule:** All leaf nodes render title-first. `content` does not occupy default canvas space and appears only in hover disclosure.
  - **Leaf scope handling:** `inner` and `outer` remain valid semantic markers for styling and interaction, but they do not impose geometry rules in the layout solve.
  - **Leaf layout family:** Leaf layout uses a static `d3-force` graph solve with link force, collision force, many-body separation, and weak centering. The solve runs when the leaf payload changes and then freezes to preserve spatial stability.
  - **Determinism rule:** Both layout pipelines use deterministic seed ordering so revisiting the same payload yields approximately stable geometry instead of visually unrelated positions.
  - **Shared canvas rule:** Branch and leaf layouts project into the same stable canvas shell. Layout changes must not change the outer shell height or the breadcrumb/loading/error overlay contract.
- **Interactions:**
  - Entering a branch view computes only the branch bubble layout for the current `children[]`.
  - Clicking a branch bubble transitions to the next taxonomy payload and recomputes the corresponding branch or leaf layout inside the same mounted canvas.
  - Entering a leaf view computes both nodes and edges together from the returned one-hop graph payload.
  - Hovering a leaf node reveals its `content` without changing the underlying graph geometry.
  - Breadcrumb jumps discard the current layout result and compute the selected ancestor state using the same deterministic layout rules.

## Validation
- **Checks:**
  - Branch view displays weighted bubbles with logarithmic size scaling and no hierarchy edges.
  - Branch composition reads as a center-out floating field with visible breathing room and no persistent overlap.
  - Branch and leaf views no longer share one generic radial layout function.
  - Leaf view renders both nodes and edges from the one-hop payload.
  - Leaf nodes display only titles by default and reveal `content` on hover.
  - Leaf layout uses relation-driven geometry without forcing `inner` and `outer` into separate positional rings.
  - Re-entering the same payload yields approximately stable node positions rather than large random jumps.
  - Layout updates preserve the single-canvas shell geometry defined in `taxonomy-view-shell.md`.
- **Evidence:**
  - Updated frontend design and implementation artifacts in `apps/web` reflect the branch and leaf layout contracts.
  - Focused frontend verification covers branch drill-down, leaf graph rendering, and hover disclosure behavior.
  - Browser-level visual inspection confirms branch composition matches the approved Figma direction and leaf graph remains readable inside the stable shell.
