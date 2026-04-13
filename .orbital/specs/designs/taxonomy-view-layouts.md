---
abstract: Frontend layout and visual-language design for branch and leaf taxonomy views inside the single taxonomy canvas host.
out_of_scope: Taxonomy API payload semantics, page-shell chrome structure, and repository-link or authentication behavior.
---

# Design: taxonomy-view-layouts

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted layout behavior and visual language for branch and leaf browsing inside the taxonomy page canvas so branch navigation and leaf relation reading each use fit-for-purpose geometry while aligning to the approved Figma presentation for both branch and leaf modes.
- **Scope/Boundaries:** Covers branch bubble sizing and placement, leaf graph level-of-detail behavior, Figma-aligned bubble composition, hover-content behavior, typography, Tailwind-first styling boundaries, viewport-driven hydration, and layout-stability rules for `apps/web`. Excludes taxonomy payload ownership, page-shell header and overlay structure, and backend graph semantics beyond the consumed skeleton/detail contracts.
- **Related Requirements:** R-001, R-003, R-004, R-006.

## Constraint Projection
- **Governing Constraints:** Frontend behavior stays within the unified web client, consumes generated taxonomy contracts without ad hoc HTTP access, preserves explicit module boundaries, and keeps behavior-changing layout decisions synchronized in active specs.
- **Detail Commitments:** Branch and leaf views use separate layout and rendering pipelines inside the same taxonomy canvas host. Branch layout is a weighted floating bubble field derived from the current layer's taxonomy children and is rendered through the branch React Flow scene. Leaf layout is a two-stage one-hop relation browser rendered through a dedicated deck.gl scene: point-mode skeleton first, then viewport-scoped card hydration after zoom activation. Branch nodes keep the approved bubble treatment, while hydrated leaf nodes upgrade into Figma-aligned cards centered on their point anchors. Page-owned styling is expressed primarily through Tailwind utility classes.
- **Update Rule:** Requirements remain stable at the repository-governance layer while branch and leaf layout rules, geometry constraints, and interaction-facing visual behavior are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Root and branch `children[]` payloads from taxonomy view queries.
  - Leaf skeleton `nodes[]` and `edges[]` payloads from taxonomy view queries.
  - Leaf detail batches containing `title` and `content` for explicit node ids.
  - Approved Figma reference for branch bubble composition: file `WBYs6P9HMxe21TSYQL637r`, node `6:3`.
  - Approved Figma reference for leaf point mode and card upgrade direction: file `WBYs6P9HMxe21TSYQL637r`, node `91:227`.
  - Existing single-canvas page shell defined in `taxonomy-view-shell.md`.
- **Outputs:**
  - One branch-specific node layout result for current-layer taxonomy bubbles.
  - One leaf-specific point/bubble presentation result for one-hop relation browsing.
  - One branch bubble presentation system aligned with Figma file `WBYs6P9HMxe21TSYQL637r`, node `6:3`.
  - One leaf point/card presentation system aligned with Figma file `WBYs6P9HMxe21TSYQL637r`, node `91:227`.
  - Stable geometry rules that can be projected into `TaxonomyViewPage.tsx` and supporting layout helpers.
- **Artifacts:**
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/index.css`
  - Supporting frontend layout helpers under `apps/web/src/features/taxonomy-view/` when implementation begins.

## Design Approach
- **Approach:** Use two dedicated client-owned layout pipelines inside the shared taxonomy canvas host. Branch layout prioritizes weighted category browsing and visual breathing room over explicit edge rendering and remains mounted through the React Flow branch renderer. Leaf layout prioritizes relation readability and interaction performance through level-of-detail rendering in a dedicated deck.gl scene: skeleton points plus true edges by default, viewport-scoped card hydration only after zoom activation, and node content available through hover instead of default canvas occupancy. Leaf performance architecture is explicitly split into high-frequency camera/world updates and low-frequency React/DOM overlay synchronization so deck-driven movement does not force full React rerenders on every drag frame. Branch and leaf therefore use separate visual systems that match their approved Figma references while preserving one stable graph coordinate space.
- **Key Elements:**
  - **Branch view role:** Branch view is a floating bubble navigator for the current taxonomy level. It is not a tree diagram and does not render hierarchy edges.
  - **Branch size encoding:** Each branch bubble radius is derived from `descendant_card_count` using logarithmic scaling so large branches read as more important without overwhelming the canvas.
  - **Branch layout family:** Branch layout uses a seeded radial force pipeline. A deterministic center-out seed initializes bubble positions, then a short static `d3-force` solve applies collision avoidance, weak centering, and weak radial cohesion. The solve freezes after layout settles; the branch view does not run continuous physics.
  - **Branch spatial rule:** Larger bubbles preferentially occupy the central zone while smaller bubbles settle farther outward. The final composition should preserve open space and resemble the approved Figma bubble field rather than a tightly packed chart or a hierarchical flow diagram.
  - **Branch bubble composition:** Branch nodes are rendered as Figma-style bubbles rather than plain circular cards. The composition includes a soft halo, a pale cool surface, a restrained core glow, a light sheen layer, and centered label typography. The branch node surface does not show auxiliary affordance copy such as `Open`.
  - **Branch typography rule:** Branch labels use the approved bubble typography direction: medium-weight, tightly centered, visually compact line-height, restrained negative tracking, and size scaling that stays legible across varying bubble diameters.
  - **Leaf view role:** Leaf view is a one-hop relation graph browser. It renders the returned `nodes[]` and `edges[]` payload together and uses geometric structure to expose relational proximity rather than taxonomy hierarchy.
  - **Leaf level-of-detail rule:** Leaf view has two rendering modes. Point mode is the default whole-graph overview and uses lightweight data points plus true graph edges with no titles or content. Card mode is activated only after the approved zoom threshold and only for nodes inside the active viewport plus overscan.
  - **Leaf renderer rule:** Leaf rendering is owned by a dedicated deck.gl scene using an orthographic 2D camera model and deck.gl scene primitives.
  - **Leaf performance-boundary rule:** Leaf camera movement is owned by a high-frequency viewport store that is decoupled from React component state. Dragging or zooming the deck scene may update this store every frame, but React-owned card hydration, hover disclosure, and DOM overlay synchronization must observe it through throttled or frame-bounded snapshots rather than through immediate full-tree rerender triggers.
  - **Leaf world-model rule:** Leaf world geometry is split into a persistent world model and a viewport-derived presentation model. World-node anchors, edge geometry, adjacency maps, and solved graph layout are computed only when the leaf payload changes. Viewport movement must not rebuild those world-model artifacts.
  - **Leaf point-mode rule:** Entering a leaf renders the full one-hop skeleton graph as points and edges without requesting or displaying node `title` or `content`.
  - **Leaf point visual rule:** Point mode aligns with the approved Figma point graph: edges remain visible as the actual graph edges, points are small and restrained, `inner` points can read slightly stronger than `outer` points, and the overall presentation is a light structural graph rather than a bubble field.
  - **Leaf layer rule:** Leaf edges render in a non-interactive base line layer and overview points render in a scatter layer. Hydrated leaf cards that must display shared rich text are rendered through a DOM overlay layer anchored to leaf graph coordinates rather than through GPU text primitives that only support plain-string drawing.
  - **Leaf viewport sizing rule:** The DOM overlay projection and viewport-hydration bounds use the leaf renderer's measured container size at runtime rather than a fixed authoring-time canvas constant.
  - **Leaf hydration rule:** Card mode is driven by viewport-scoped detail hydration. The frontend requests `title` and `content` only for node ids inside the current viewport plus one overscan ring, then upgrades those nodes from points to cards.
  - **Leaf cache rule:** Hydrated node details are cached by node id for the active leaf view and reused during subsequent pans or zooms instead of being re-requested on every movement.
  - **Leaf visibility-model rule:** Visible card ids are derived from the current viewport snapshot in a dedicated visibility model. Viewport movement may change this visible-card set at most on a throttled or frame-bounded cadence; the leaf renderer must not run full hydration-set recomputation for every raw pointer move event.
  - **Leaf hydration latency rule:** Viewport-scoped hydration assumes the backend detail path validates membership and fetches details only for requested node ids. The frontend design does not depend on a backend implementation that reloads full assignment sets or full node-detail sets on every hydration request.
  - **Leaf card rule:** Hydrated leaf nodes render as shallow rectangular cards rather than circular bubbles. `content` does not occupy default canvas space and appears only in hover disclosure.
  - **Leaf anchor rule:** The card center is anchored to the original point coordinate. Hydrating a node changes its rendered footprint but does not move its graph anchor, and disclosure anchoring uses the actual DOM-rendered card box instead of a stale fixed-height estimate.
  - **Leaf card sizing rule:** Hydrated leaf cards use a small set of stable width tiers rather than freeform per-title width growth. Text wraps inside the selected tier width and card height grows with the full wrapped title instead of being normalized to one shared equal-height shell.
  - **Leaf typography rule:** Hydrated card titles are center-aligned horizontally and vertically, allow automatic wrapping, and avoid forcing long titles onto a single line. Extremely long uninterrupted tokens may use a fallback break rule to preserve containment.
  - **Leaf hover rule:** Hover disclosure is owned by a DOM overlay fed by deck.gl picking results so card `content` can remain outside the default GPU-rendered node footprint.
  - **Leaf card text rule:** Hydrated leaf card titles and hover disclosure content consume the shared knowledge-card rich-text contract defined in `web-knowledge-card-rich-text.md`.
  - **Leaf anchoring rule for rich text:** DOM-rendered leaf cards remain anchored to the same graph coordinates used by the deck scene so viewport movement, hover focus, and card hydration continue to behave like one integrated leaf renderer rather than two unrelated layers.
  - **Leaf overlay virtualization rule:** The DOM rich-text overlay is a low-frequency presentation layer that renders only the currently visible hydrated cards plus bounded overscan. It must not mirror the full leaf graph as DOM.
  - **Leaf rich-text caching rule:** Markdown and KaTeX work for card titles and hover content is keyed by stable text input and reused across viewport movement. Camera motion alone must not cause repeated rich-text parsing for unchanged card text.
  - **Leaf scope handling:** `inner` and `outer` remain valid semantic markers for styling and interaction, but they do not impose geometry rules in the layout solve.
  - **Leaf layout family:** Leaf layout uses a static `d3-force` graph solve with link force, collision force, many-body separation, and weak centering. The solve runs when the leaf payload changes and then freezes to preserve spatial stability.
  - **Leaf hydration stability rule:** Hydrating or remeasuring cards does not rerun the solved world layout. Point-mode node centers remain the canonical graph anchors, while later hydration passes only update card box dimensions and anchored overlay presentation around those fixed centers.
  - **Leaf measurement rule:** DOM card measurement is write-back metadata rather than a per-frame layout driver. Cards may be measured on first render, on text change, on width-tier change, or on explicit invalidation, but viewport panning and zooming alone must not trigger full-card-set synchronous box reads.
  - **Leaf rectangle collision rule:** When nodes are upgraded into cards, the layout layer must reserve space from the card footprint approximation derived from the selected width tier and estimated wrapped-title height rather than from the old circular point radius.
  - **Leaf scope styling rule:** `inner` and `outer` can differ only through restrained variations such as border emphasis, label tone, or surface tint. They do not become separate component families.
  - **Hover disclosure rule:** Leaf `content` is revealed through a lightweight floating disclosure that visually belongs to the canvas and bubble system. The disclosure remains outside the default node footprint, anchors tightly to the hovered card rather than to the cursor, prefers a short gap beneath the card, flips above only when lower space is insufficient, and does not use a generic dark tooltip treatment.
  - **Hover focus rule:** Hovering a hydrated leaf card triggers a local focus state. The hovered card is the strongest visual focus, directly connected cards receive a secondary highlight treatment, incident edges are highlighted, and non-connected cards and edges are visibly weakened without being removed from the scene. Card emphasis changes must preserve card footprint and typography size stability; focus differentiation is carried by color and opacity rather than card scaling.
  - **Zoom activation rule:** Card hydration is gated by one explicit zoom threshold. Below the threshold, all leaf nodes remain in point mode and no title/content detail requests are sent.
  - **Viewport rule:** When card mode is active, only nodes inside the viewport plus overscan may render as cards. Nodes outside that region remain points even if their details are already cached.
  - **Movement rule:** Panning or viewport changes trigger incremental detail hydration only for newly entered overscan nodes. Already hydrated nodes reuse cache entries.
  - **Tailwind-first implementation rule:** Bubble composition, spacing, typography, and disclosure styling are carried primarily through Tailwind utility classes colocated with the React structure. Handwritten CSS is reserved only for library overrides or visual effects that cannot be expressed cleanly through utilities.
  - **Determinism rule:** Both layout pipelines use deterministic seed ordering so revisiting the same payload yields approximately stable geometry instead of visually unrelated positions.
  - **Shared canvas rule:** Branch and leaf layouts project into the same stable canvas shell. Layout changes must not change the outer shell height or the breadcrumb/loading/error overlay contract.
  - **Renderer-swappability rule:** The canvas host treats branch and leaf renderers as swappable scene implementations behind one stable shell contract.
- **Interactions:**
  - Entering a branch view computes only the branch bubble layout for the current `children[]`.
  - Clicking a branch bubble transitions to the next taxonomy payload and recomputes the corresponding branch or leaf layout inside the same mounted canvas.
  - Entering a leaf view computes the one-hop layout from the returned skeleton payload and renders all nodes in point mode with the true graph edges still visible inside the deck.gl scene.
  - Crossing the card-activation zoom threshold computes the active viewport plus overscan set from the throttled viewport snapshot and hydrates leaf node details only for that region.
  - Panning inside card mode incrementally hydrates newly entered overscan nodes while leaving far-away nodes in point mode, and card overlay synchronization is allowed to trail camera motion by a small bounded delay to preserve interaction smoothness.
  - Hydrating a node upgrades its rendered shape from point to card while keeping the point coordinate as the card center anchor.
  - Hovering a hydrated leaf card reveals its `content` without changing the underlying graph geometry.
  - Hovering a hydrated leaf card also highlights its incident edges and directly connected cards while visually muting unrelated cards and edges.
  - Breadcrumb jumps discard the current layout result and compute the selected ancestor state using the same deterministic layout rules.

## Validation
- **Checks:**
  - Branch view displays weighted bubbles with logarithmic size scaling and no hierarchy edges.
  - Branch composition reads as a center-out floating field with visible breathing room and no persistent overlap.
  - Branch nodes read as the approved bubble family and hydrated leaf nodes read as the approved rectangular card family.
  - Branch bubbles do not display auxiliary affordance text such as `Open`.
  - Branch and leaf views use separate dedicated layout functions matched to their respective visual systems.
  - Leaf view renders the skeleton graph from the one-hop payload without loading titles or content on entry.
  - Leaf view uses deck.gl scene primitives for points and edges, while rich-text leaf cards render through a coordinate-anchored DOM overlay layer.
  - Leaf camera motion remains smooth because deck.gl view-state updates do not force whole-tree React rerenders on every pointer frame.
  - Leaf view displays nodes as points below the zoom threshold and upgrades only viewport-scoped hydrated nodes into cards above the threshold.
  - Leaf node details are requested only for the viewport plus overscan region and are reused from cache during continued navigation.
  - Viewport-scoped leaf hydration remains responsive because detail requests are bounded to the requested node ids and do not trigger whole-graph detail reads on the backend.
  - Hydrated leaf nodes display only titles by default and reveal `content` on hover.
  - Hydrated leaf card titles and hover disclosure content use the shared knowledge-card rich-text renderer instead of raw string rendering.
  - Dragging or zooming the leaf scene does not trigger full-card-set synchronous DOM measurement or repeated markdown/KaTeX parsing for unchanged text.
  - Hovering a hydrated leaf card makes the hovered card strongest, connected cards secondarily highlighted, incident edges highlighted, and unrelated cards and edges weakened.
  - Hydrated leaf cards are center-anchored to the original point coordinates, use stable discrete width tiers with automatic line wrapping, and grow in height with the wrapped title line count instead of flattening to equal-height shells.
  - Breadcrumb, leaf point graph, leaf card typography, and disclosure styling remain visually aligned with the approved Figma direction.
  - Page-owned layout styling is carried primarily by Tailwind utility classes rather than large handwritten CSS blocks.
  - Leaf layout uses relation-driven geometry without forcing `inner` and `outer` into separate positional rings.
  - Re-entering the same payload yields approximately stable node positions rather than large random jumps.
  - Layout updates preserve the single-canvas shell geometry defined in `taxonomy-view-shell.md`.
- **Evidence:**
  - Updated frontend design and implementation artifacts in `apps/web` reflect the branch and leaf layout contracts.
  - Focused frontend verification covers branch drill-down, leaf point-mode entry, viewport-scoped leaf hydration, and hover disclosure behavior.
  - Browser-level visual inspection confirms branch composition matches the approved Figma direction and leaf graph remains readable as points at overview scale and as hydrated cards at local scale inside the stable shell.
