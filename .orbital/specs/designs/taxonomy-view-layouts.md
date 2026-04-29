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
- **Scope/Boundaries:** Covers branch/root bubble sizing and placement, leaf graph level-of-detail behavior, Figma-aligned branch bubble composition, hover and selected content disclosure behavior, disclosure edit affordance behavior, typography, Tailwind-first styling boundaries, viewport-driven title hydration, and layout-stability rules for `apps/web`. Excludes taxonomy payload ownership, page-shell header and overlay structure, and backend graph semantics beyond the consumed skeleton/detail contracts.
- **Related Requirements:** R-001, R-003, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Frontend behavior stays within the unified web client, consumes taxonomy view data through BFF-owned web data adapters, preserves explicit module boundaries, and keeps behavior-changing layout decisions synchronized in active specs.
- **Detail Commitments:** Branch and leaf views use separate layout and rendering pipelines inside the same taxonomy canvas host. Branch layout is a responsive weighted floating bubble field derived from the current layer's taxonomy children and rendered through the branch React Flow scene. The branch/root presentation follows the approved desktop and mobile Graph View frames. Leaf layout is a two-stage one-hop relation browser rendered through a dedicated deck.gl scene: point-mode skeleton first, then viewport-scoped point-title labels after zoom activation. Leaf rendering inherits the shared desktop and mobile taxonomy canvas shell while leaf-internal point, label, edge, hover, selected, neighbor, and dimmed behavior stays governed by the accepted leaf layout rules. Page-owned styling is expressed primarily through Tailwind utility classes.
- **Update Rule:** Requirements remain stable at the repository-governance layer while branch and leaf layout rules, geometry constraints, and interaction-facing visual behavior are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Root and branch `children[]` payloads from taxonomy view queries.
  - Leaf skeleton `nodes[]` and `edges[]` payloads from taxonomy view queries.
  - Leaf title batches containing `title` for explicit node ids.
  - Leaf content detail batches containing `title`, `content`, and `current_version` for interacted point ids in point-title mode.
  - Approved Figma reference for branch/root Graph View composition: file `WBYs6P9HMxe21TSYQL637r`, desktop node `702:3845`, mobile node `702:3950`, desktop content component node `702:2514`, and mobile content component node `702:2555`.
  - Approved Figma references for leaf point mode, point-title mode, content disclosure, and no-selection states in file `WBYs6P9HMxe21TSYQL637r`: component nodes `818:353`, `818:360`, and `844:531`; desktop content nodes `799:743`, `808:303`, `834:1469`, and `834:2492`; mobile content nodes `799:744`, `808:441`, `834:2005`, and `834:3028`.
  - Single-canvas page shell defined in `taxonomy-view-shell.md`.
- **Outputs:**
  - One branch-specific node layout result for current-layer taxonomy bubbles.
  - One leaf-specific point, point-title, focus, and disclosure presentation result for one-hop relation browsing.
  - One responsive branch bubble presentation system aligned with Figma file `WBYs6P9HMxe21TSYQL637r`, desktop node `702:3845` and mobile node `702:3950`.
  - One leaf point, point-title, edge, hover-disclosure, selected-disclosure, and no-selection presentation system aligned with Figma file `WBYs6P9HMxe21TSYQL637r`, with hover and selected disclosures sharing the same visual card shell.
  - Stable geometry rules that can be projected into `TaxonomyViewPage.tsx` and supporting layout helpers.
- **Artifacts:**
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/index.css`
  - Supporting frontend layout helpers under `apps/web/src/features/taxonomy-view/` when implementation begins.

## Design Approach
- **Approach:** Use two dedicated client-owned layout pipelines inside the shared taxonomy canvas host. Branch/root layout prioritizes weighted category browsing and visual breathing room over explicit edge rendering and remains mounted through the React Flow branch renderer. Branch/root layout projects the approved desktop and mobile Graph View compositions into responsive runtime geometry rather than hardcoded sample coordinates. Leaf layout prioritizes relation readability and interaction performance through level-of-detail rendering in a dedicated deck.gl scene: skeleton points plus true edges by default, viewport-scoped point-title labels after zoom activation, and node content available through hover or selected disclosure outside the default graph footprint. Leaf performance architecture is explicitly split into a high-frequency camera path, a throttled visibility and hydration path, and a camera-synchronous DOM overlay position path so deck-driven movement does not force full React rerenders on every drag frame while visible labels and disclosures stay locked to graph coordinates. Branch and leaf therefore use separate visual systems while sharing the stable desktop/mobile taxonomy canvas shell.
- **Key Elements:**
  - **Branch view role:** Branch view is a floating bubble navigator for the current taxonomy level. It is not a tree diagram and does not render hierarchy edges.
  - **Branch size encoding:** Each branch bubble radius is derived from `descendant_card_count` using logarithmic scaling so large branches read as more important without overwhelming the canvas.
  - **Branch layout family:** Branch layout uses a seeded radial force pipeline. A deterministic center-out seed initializes bubble positions, then a short static `d3-force` solve applies collision avoidance, weak centering, and weak radial cohesion. The solve freezes after layout settles; the branch view does not run continuous physics.
  - **Branch responsive viewport rule:** Branch layout uses the measured taxonomy canvas size to select runtime geometry. The desktop reference viewport is `1120px x 1024px`. The mobile reference viewport is `440px x 892px`. Intermediate widths scale between those references while preserving visual spacing and containment.
  - **Branch spatial rule:** Larger bubbles preferentially occupy stronger visual positions while smaller bubbles settle into secondary positions. The final composition should preserve open space and resemble the approved desktop and mobile Figma bubble fields rather than a tightly packed chart or a hierarchical flow diagram.
  - **Branch bubble composition:** Branch nodes are rendered as Figma-style bubbles rather than plain circular cards. The composition includes a soft halo, a pale cool surface, and centered label typography. The branch node surface does not show auxiliary affordance copy such as `Open`.
  - **Branch desktop size rule:** Desktop branch bubbles use the approved content-frame scale family, with representative visual diameters around `146px`, `172px`, `212px`, and `236px` depending on taxonomy weight and label density.
  - **Branch mobile size rule:** Mobile branch bubbles use the approved content-frame scale family, with representative visual diameters around `100px` to `132px` depending on taxonomy weight and label density.
  - **Branch typography rule:** Branch labels use the approved bubble typography direction: medium-weight, tightly centered, visually compact line-height, normal tracking, and size scaling that stays legible across varying bubble diameters.
  - **Leaf view role:** Leaf view is a one-hop relation graph browser. It renders the returned `nodes[]` and `edges[]` payload together and uses geometric structure to expose relational proximity rather than taxonomy hierarchy.
  - **Leaf level-of-detail rule:** Leaf view has two rendering modes. Point mode is the default whole-graph overview and uses lightweight data points plus true graph edges with no titles, content, hover, click, selection, or disclosure interaction. Point-title mode activates when the deck orthographic viewport zoom is greater than or equal to `0.85` and displays viewport-scoped title labels centered under their points while keeping the point glyphs visible.
  - **Leaf renderer rule:** Leaf rendering is owned by a dedicated deck.gl scene using an orthographic 2D camera model and deck.gl scene primitives.
  - **Leaf performance-boundary rule:** Leaf camera movement is owned by a high-frequency viewport store that is decoupled from React component state. Dragging or zooming the deck scene may update this store every frame, but only hydration, visible-title-set recomputation, and other data-side overlay work observe it through throttled or frame-bounded snapshots. Visible title labels and disclosure positions must stay camera-synchronous without requiring full-tree React rerenders on every pointer frame.
  - **Leaf world-model rule:** Leaf world geometry is split into a persistent world model and a viewport-derived presentation model. World-node anchors, edge geometry, adjacency maps, and solved graph layout are computed only when the leaf payload changes. Viewport movement must not rebuild those world-model artifacts.
  - **Leaf point-mode rule:** Entering a leaf renders the full one-hop skeleton graph as points and edges without requesting or displaying node `title` or `content`.
  - **Leaf point visual rule:** Point mode aligns with the approved Figma point graph: edges remain visible as the actual graph edges, points share one `8px` diameter, `inner` and `outer` distinction is carried by tokenized opacity, and the overall presentation is a light structural graph rather than a bubble field.
  - **Leaf point-title visual rule:** Point-title mode keeps the same graph points and edges visible while adding centered title labels below points. Title labels have no container fill, stroke, or shadow and stay centered to their node anchor.
  - **Leaf layer rule:** Leaf edges render in deck.gl line layers and overview points render in a deck.gl scatter layer. Leaf title labels and hover or selected content disclosures render through DOM overlay layers anchored to leaf graph coordinates because knowledge-card text needs the shared rich-text renderer.
  - **Leaf viewport sizing rule:** The DOM overlay projection and viewport-hydration bounds use the leaf renderer's measured container size at runtime rather than a fixed authoring-time canvas constant.
  - **Leaf title hydration rule:** Point-title mode is driven by viewport-scoped title hydration. The frontend requests `title` for node ids inside the current viewport plus one overscan ring, then uses the title for the label overlay.
  - **Leaf interaction target rule:** In point-title mode, hover and click interaction targets are the point glyphs. Point-title labels are display-only and do not receive hover, click, focus, or selected-state events.
  - **Leaf on-demand content rule:** Hovering or selecting a point glyph in point-title mode requests that node's disclosure detail when it is missing from cache. Disclosure detail contains `title`, `content`, and `current_version`; cached title data may be reused while content and version remain interaction-driven.
  - **Leaf cache rule:** Hydrated node titles and disclosure details are cached by node id for the active leaf view and reused during subsequent pans, zooms, hover, and selected disclosure display instead of being re-requested on every movement.
  - **Leaf visibility-model rule:** Visible title-label ids are derived from the current viewport snapshot in a dedicated visibility model. Viewport movement may change this visible-title set at most on a throttled or frame-bounded cadence; the leaf renderer must not run full hydration-set recomputation for every raw pointer move event.
  - **Leaf hydration latency rule:** Viewport-scoped title hydration assumes the backend validates membership and fetches title data only for requested node ids. Interaction-driven disclosure detail assumes the backend validates membership and fetches content only for requested node ids. The frontend design does not depend on a backend implementation that reloads full assignment sets or full node-detail sets on every hydration request.
  - **Leaf selected state rule:** Clicking a point glyph in point-title mode makes that node the persistent focus source. Clicking the selected point glyph clears selection. Clicking empty canvas space clears selection. Point-title labels and selected disclosure interactions do not clear selection.
  - **Leaf focus source rule:** When a node is selected, selected focus is the only graph-wide focus source. Hovering another node applies only local point hover feedback to that node; active edges, neighbor halos, dimming, and disclosure remain tied to the selected node.
  - **Leaf hover state rule:** When no node is selected, hovering a point glyph in point-title mode makes the hovered node the transient focus source and displays a transient title-plus-content hover disclosure after disclosure detail is available.
  - **Leaf neighbor semantics:** The focused node shows the selected or hover emphasis. Direct graph neighbors connected by an edge receive the neighbor treatment and incident edges use the active edge treatment. Nodes without a direct focused-node edge do not receive neighbor halos.
  - **Leaf dimming semantics:** When a focus source exists, non-focused and non-neighbor nodes and non-incident edges use dimmed opacity while preserving their positions, sizes, and labels.
  - **Leaf no-selection rule:** When no node is selected and no node is hovered, all nodes and edges use their base visual treatment. No halo, focus ring, active edge, dimming, hover disclosure, or selected disclosure is visible.
  - **Leaf disclosure rule:** Leaf `title` and `content` are revealed through a lightweight floating disclosure that visually belongs to the canvas. Hover disclosures are transient and include the hovered node title plus content. Selected disclosures are persistent and include the selected node title plus content. Hover and selected disclosures use the same visual card shell; mode only controls transient versus persistent behavior. The disclosure card uses an `8px` radius token, a fixed-height responsive size family, and a vertically scrollable content region with a thin shadcn-style scrollbar. Breakpoint card sizes are `320px x 160px` at `md`, `352px x 176px` at `lg`, `384px x 192px` at `xl`, and `416px x 208px` at `2xl`; content scroll-region heights are `96px`, `112px`, `128px`, and `144px` respectively. Both hover and selected disclosures include the Figma edit affordance in the header, stay centered to the target point, and sit near the target point.
  - **Leaf disclosure edit rule:** The disclosure edit affordance opens the same Suggest Edit interface used by Search result cards. The suggestion payload uses the disclosure node id, title, content, and `current_version` as the base version. Disclosure edit-button interaction must not clear selected state or trigger canvas clicks.
  - **Leaf disclosure priority rule:** When a selected node exists, only the selected disclosure is visible. Hovering another node does not display a second disclosure and does not replace the selected disclosure.
  - **Leaf disclosure-title rule:** In point-title mode, the disclosure target node hides its point-title label while that node's title-plus-content disclosure is visible. The target title moves into the disclosure. When the disclosure disappears, the node's title label is restored if the node remains in the visible title set. When a selected disclosure exists, hovering another node does not create a hover disclosure and does not hide the hovered node label.
  - **Leaf label text rule:** Point-title labels, hover disclosure titles, hover disclosure content, selected disclosure titles, and selected disclosure content consume the shared knowledge-card rich-text contract defined in `web-knowledge-card-rich-text.md`.
  - **Leaf anchoring rule for rich text:** DOM-rendered title labels and disclosures remain anchored to the same graph coordinates used by the deck scene so viewport movement, hover focus, selection, and hydration behave like one integrated leaf renderer rather than unrelated layers.
  - **Leaf overlay motion rule:** Once a title label or disclosure is mounted, its screen position is synchronized from the live deck viewport on every camera frame through imperative DOM transform updates rather than through throttled React rerenders. Camera motion may be throttled for hydration and visibility decisions, but not for already visible overlay motion.
  - **Leaf overlay virtualization rule:** The DOM rich-text overlay is a low-frequency presentation layer that renders only the currently visible title labels plus bounded overscan and the active hover or selected disclosure. It must not mirror the full leaf graph as DOM.
  - **Leaf rich-text caching rule:** Markdown and KaTeX work for title labels and disclosure content is keyed by stable text input and reused across viewport movement. Camera motion alone must not cause repeated rich-text parsing for unchanged text.
  - **Leaf scope handling:** `inner` and `outer` remain valid semantic markers for styling and interaction, but they do not impose geometry rules in the layout solve.
  - **Leaf layout family:** Leaf layout uses a static `d3-force` graph solve with link force, point-sized collision force, many-body separation, and weak centering. Collision spacing protects the 8px point glyphs only; title labels and disclosures remain overlay presentation and must not reserve card-sized space in the solved graph. The solve runs when the leaf payload changes and then freezes to preserve spatial stability.
  - **Leaf hydration stability rule:** Hydrating node titles, hydrating disclosure details, or rendering title labels does not rerun the solved world layout. Point-mode node centers remain the canonical graph anchors, while overlay presentation is positioned around those fixed centers.
  - **Leaf measurement rule:** DOM label and disclosure measurement is presentation metadata rather than a per-frame layout driver. Labels and disclosures may be measured on first render, on text change, on viewport-class change, or on explicit invalidation, but viewport panning and zooming alone must not trigger full-overlay-set synchronous box reads.
  - **Leaf scope styling rule:** `inner` and `outer` differ only through tokenized point opacity on the shared point color. They do not differ by size, border, label tone, surface tint, or component family.
  - **Hover disclosure placement rule:** Hover disclosure anchors to the hovered point coordinate, prefers a short gap beneath the point, flips above only when lower space is insufficient, and does not use a generic dark tooltip treatment.
  - **Selected disclosure placement rule:** Selected disclosure anchors to the selected node coordinate, remains horizontally centered to that point, and uses the shared responsive disclosure card size family.
  - **Zoom activation rule:** Point-title hydration and point interaction are gated by deck orthographic viewport zoom `0.85`. Below `0.85`, all leaf nodes remain in non-interactive point mode. At or above `0.85`, point-title mode is active and point glyphs can be hovered or clicked.
  - **Viewport rule:** When point-title mode is active, only nodes inside the viewport plus overscan may render title labels. Nodes outside that region remain points even if their details are already cached.
  - **Movement rule:** Panning or viewport changes trigger incremental title hydration only for newly entered overscan nodes. Already hydrated node titles and disclosure details reuse cache entries.
  - **Tailwind-first implementation rule:** Bubble composition, spacing, typography, and disclosure styling are carried primarily through Tailwind utility classes colocated with the React structure. Handwritten CSS is reserved only for library overrides or visual effects that cannot be expressed cleanly through utilities.
  - **Determinism rule:** Both layout pipelines use deterministic seed ordering so revisiting the same payload yields approximately stable geometry instead of visually unrelated positions.
  - **Shared canvas rule:** Branch and leaf layouts project into the same stable canvas shell. Layout changes must not change the outer shell height or the breadcrumb/loading/error overlay contract.
  - **Renderer-swappability rule:** The canvas host treats branch and leaf renderers as swappable scene implementations behind one stable shell contract.
- **Interactions:**
  - Entering a branch view computes only the branch bubble layout for the current `children[]`.
  - Clicking a branch bubble transitions to the next taxonomy payload and recomputes the corresponding branch or leaf layout inside the same mounted canvas.
  - Entering a leaf view computes the one-hop layout from the returned skeleton payload and renders all nodes in point mode with the true graph edges still visible inside the deck.gl scene.
  - Crossing deck orthographic viewport zoom `0.85` computes the active viewport plus overscan set from the throttled viewport snapshot and hydrates leaf titles only for that region.
  - Panning inside point-title mode incrementally hydrates newly entered overscan nodes while leaving far-away nodes in point mode, and already visible labels remain visually locked to live camera motion while hydration and visibility decisions continue on the bounded snapshot cadence.
  - Hydrating a node for point-title mode adds title data to the cache while keeping the point coordinate as the graph anchor.
  - Hovering or selecting a point glyph in point-title mode adds disclosure detail to the cache as needed.
  - Hovering a point glyph in point-title mode when no selected node exists reveals its `content` without changing the underlying graph geometry.
  - Hovering a point glyph in point-title mode when no selected node exists highlights its incident edges and directly connected nodes while visually muting unrelated nodes and edges.
  - Selecting a point glyph in point-title mode reveals a persistent title-plus-content disclosure and makes that node the graph-wide focus source.
  - Clicking the edit affordance in a hover or selected disclosure opens the shared Suggest Edit dialog for that node.
  - Hovering another node while a selected node exists applies only local point hover feedback and leaves the selected focus source and selected disclosure unchanged.
  - Clicking empty canvas space or the selected point glyph clears selection and returns the graph to no-selection state unless another point hover is active.
  - Breadcrumb jumps discard the current layout result and compute the selected ancestor state using the same deterministic layout rules.

## Validation
- **Checks:**
  - Branch view displays weighted bubbles with logarithmic size scaling and no hierarchy edges.
  - Branch composition reads as a floating field with visible breathing room and no persistent overlap at both desktop and mobile canvas sizes.
  - Branch layout uses the approved desktop `1120px x 1024px` content reference and mobile `440px x 892px` content reference as responsive geometry anchors.
  - Branch nodes read as the approved bubble family and leaf nodes read as the approved point, point-title, neighbor, selected, dimmed, and no-selection component family.
  - Branch bubbles do not display auxiliary affordance text such as `Open`.
  - Branch bubble diameter tiers, label widths, and text sizes remain visually aligned with the approved desktop and mobile Graph View frames.
  - Branch and leaf views use separate dedicated layout functions matched to their respective visual systems.
  - Leaf view renders the skeleton graph from the one-hop payload without loading titles or content on entry.
  - Leaf view uses deck.gl scene primitives for points and edges, while rich-text title labels and disclosures render through coordinate-anchored DOM overlay layers.
  - Leaf camera motion remains smooth because deck.gl view-state updates do not force whole-tree React rerenders on every pointer frame.
  - Leaf view displays non-interactive nodes as points below the zoom threshold and adds viewport-scoped title labels plus point-glyph interaction above the threshold.
  - Leaf node titles are requested only for the viewport plus overscan region and are reused from cache during continued navigation.
  - Leaf node content is requested only for hover or selected disclosure targets and is reused from cache during continued interaction.
  - Viewport-scoped leaf title hydration remains responsive because title requests are bounded to the requested node ids and do not trigger whole-graph detail reads on the backend.
  - Point-title labels display title text under points without a fill, stroke, or card container and do not own hover or click interaction.
  - Point-title labels, hover disclosure title, hover disclosure content, selected disclosure title, and selected disclosure content use the shared knowledge-card rich-text renderer instead of raw string rendering.
  - Hover and selected disclosures show the Figma-aligned edit affordance and route it through the shared Suggest Edit flow with the node's current version.
  - Hover and selected disclosures share one visual card shell, use the tokenized `8px` disclosure radius, use the accepted `md`, `lg`, `xl`, and `2xl` fixed card size family, and keep overflow content inside the disclosure content scroll region.
  - Dragging or zooming the leaf scene does not trigger full-overlay-set synchronous DOM measurement or repeated markdown/KaTeX parsing for unchanged text.
  - Hovering a point glyph in point-title mode with no selection makes the hovered node strongest, connected nodes secondarily highlighted, incident edges highlighted, and unrelated nodes and edges weakened.
  - Selecting a point glyph in point-title mode makes the selected node strongest, connected nodes secondarily highlighted, incident edges highlighted, unrelated nodes and edges weakened, and the selected disclosure visible.
  - Hovering another node while selection exists does not change the selected disclosure or graph-wide focus source.
  - Clicking empty canvas space or clicking the selected point glyph again clears selected focus.
  - Breadcrumb, branch bubbles, leaf point graph, point-title labels, and disclosure styling remain visually aligned with the approved Figma direction.
  - Page-owned layout styling is carried primarily by Tailwind utility classes rather than large handwritten CSS blocks.
  - Leaf layout uses relation-driven geometry without forcing `inner` and `outer` into separate positional rings.
  - Re-entering the same payload yields approximately stable node positions rather than large random jumps.
  - Layout updates preserve the single-canvas desktop and mobile shell geometry defined in `taxonomy-view-shell.md`.
- **Evidence:**
  - Updated frontend design and implementation artifacts in `apps/web` reflect the branch and leaf layout contracts.
  - Focused frontend verification covers branch drill-down, leaf point-mode entry, viewport-scoped title hydration, hover disclosure, selected disclosure, selected clearing, and focus-state edge/node styling.
  - Browser-level visual inspection confirms branch composition matches the approved Figma direction and leaf graph remains readable as points at overview scale and as point-title labels at local scale inside the stable shell.
