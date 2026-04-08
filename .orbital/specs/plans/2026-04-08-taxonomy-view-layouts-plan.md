---
abstract: Implementation plan for branch and leaf taxonomy view layouts using dedicated force-based pipelines inside the stable React Flow shell.
out_of_scope: Taxonomy API contract changes, page-shell chrome redesign, and authentication or repository-link behavior.
---

# Taxonomy View Layouts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-04-08-taxonomy-view-layouts-plan`

**Goal:** Implement the approved branch and leaf layout designs inside the existing taxonomy page shell: branch as a weighted floating bubble field and leaf as a static one-hop relation graph with title-first nodes and hover-revealed content.

**Architecture:** Keep the approved header + stable canvas shell intact and replace the page's shared radial placeholder layout with two explicit client-owned pipelines. Introduce focused layout helpers for branch and leaf solves, integrate `d3-force` explicitly at the frontend dependency boundary, and update the page so branch consumes only current-level bubbles while leaf consumes both nodes and edges with title-first node rendering.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-shell.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

**Assumptions and Constraints:**
- The stable page shell already exists and must remain the only page chrome.
- Branch view does not render hierarchy edges.
- Leaf view renders backend-provided one-hop edges and uses node titles as default visible content.
- Leaf node `content` is revealed on hover and does not occupy default canvas space.
- `inner` and `outer` remain valid semantic markers for styling, but they do not impose ring-based geometry in the leaf solve.
- Layout solves are static and deterministic per payload; no continuously running force simulation is allowed in the mounted page.
- The implementation must stay within the current React + TypeScript + plain CSS stack in `apps/web`.

**Decision Gates:** None open. The approved design already authorizes replacing the shared radial placeholder with separate branch and leaf layout pipelines.

**Tech Stack:**
- React 19 + TypeScript
- React Flow
- `d3-force`
- Vitest + React Testing Library
- Plain CSS in `src/index.css`
- Biome + TypeScript build checks

---

## File Structure Map

### Dependency boundary
- Modify: `/Users/mianqin/Code/knowledge/apps/web/package.json`
- Modify: `/Users/mianqin/Code/knowledge/pnpm-lock.yaml`

### Layout helpers
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayoutTypes.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildBranchLayout.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildLeafLayout.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts`

### Page integration
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/index.css`

### Spec synchronization
- Already updated in this round:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

### Structure rationale
- The current page file combines data mapping, placeholder layout math, node rendering, and shell composition in one unit. That pattern is no longer adequate because branch and leaf layouts now have distinct algorithms and test surfaces.
- This plan extracts only the responsibilities that directly serve the approved design:
  - pure branch layout solve;
  - pure leaf layout solve;
  - reusable node presentation;
  - page-level orchestration.
- This is a focused decomposition, not unrelated refactoring.

## Chunk 1: Dependency and Layout Foundations

### Task T01: Add explicit `d3-force` dependency and lock pure layout contracts with tests

**Task ID:** `T01`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/web/package.json`
- Modify: `/Users/mianqin/Code/knowledge/pnpm-lock.yaml`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayoutTypes.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildBranchLayout.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildLeafLayout.ts`
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Write the failing pure-layout tests**

Create `taxonomyLayouts.test.ts` with contract tests that do not mount React Flow:

```ts
import { describe, expect, it } from "vitest";

import { buildBranchLayout, bubbleDiameterFromDescendantCount } from "./buildBranchLayout";
import { buildLeafLayout } from "./buildLeafLayout";

describe("branch layout contracts", () => {
  it("uses logarithmic bubble sizing", () => {
    expect(bubbleDiameterFromDescendantCount(1)).toBeLessThan(
      bubbleDiameterFromDescendantCount(100),
    );
  });

  it("returns non-overlapping weighted bubbles with deterministic ids", () => {
    const result = buildBranchLayout({
      center: { x: 700, y: 450 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 30, id: 2, name: "Culture" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    expect(result.nodes).toHaveLength(2);
    expect(result.nodes[0]?.id).toBe("taxonomy-1");
    expect(result.nodes.every((node) => Number.isFinite(node.position.x))).toBe(true);
  });
});

describe("leaf layout contracts", () => {
  it("returns title-first nodes and preserves supplied edges", () => {
    const result = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [{ id: "e-1", source_node_id: 10, strength: 0.8, target_node_id: 11 }],
      nodes: [
        { content: "Inner content", id: 10, scope: "inner", title: "Inner node" },
        { content: "Outer content", id: 11, scope: "outer", title: "Outer node" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    expect(result.nodes).toHaveLength(2);
    expect(result.edges).toHaveLength(1);
    expect(result.nodes[0]?.data.label).toBe("Inner node");
    expect(result.nodes[0]?.data.content).toBe("Inner content");
  });
});
```

Include one helper assertion that checks repeated calls with identical input keep the same node ids and the same rounded positions.

- [ ] **Step 2: Run the new test file and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: FAIL because the layout helpers and dependency do not exist yet.

- [ ] **Step 3: Add the dependency and minimal helper scaffolding**

Implement:
- add `d3-force` as an explicit frontend dependency;
- define layout input/output types in `taxonomyLayoutTypes.ts`;
- create minimal `buildBranchLayout.ts` and `buildLeafLayout.ts` exports with typed signatures;
- add a shared deterministic seed utility local to the layout helpers if needed.

Avoid:
- hiding force configuration inside the page component;
- relying on transitive dependencies instead of declaring `d3-force` explicitly;
- mixing React JSX with pure layout functions.

- [ ] **Step 4: Re-run the focused layout test**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- `d3-force` is explicitly declared at the frontend dependency boundary;
- branch and leaf layout helpers exist as pure units with typed contracts;
- the spec remains current with no behavior drift.

Avoided anti-patterns:
- No workaround dependency access through transitive packages.
- No silent fallback to the old shared radial layout.
- No over-defensive helper API surface beyond the approved inputs.

Commit message shape:
- `[plan:2026-04-08-taxonomy-view-layouts-plan][task:T01] add layout helper contracts`

### Task T02: Implement seeded radial-force branch layout

**Task ID:** `T02`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildBranchLayout.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Extend the branch tests with the approved layout behavior**

Add failing tests that verify:
- larger `descendant_card_count` yields larger bubble diameter via log scaling;
- branch positions are seeded from center-out ordering rather than uniform angle stepping;
- the solve uses static settling and returns bubbles inside the viewport bounds;
- repeated solves with the same payload keep approximately stable rounded positions.

Example assertion shape:

```ts
it("prefers heavier bubbles near the center zone", () => {
  const result = buildBranchLayout({
    center: { x: 702, y: 450 },
    children: [
      { depth: 0, descendant_card_count: 500, id: 1, name: "Science" },
      { depth: 0, descendant_card_count: 5, id: 2, name: "Culture" },
    ],
    viewport: { height: 900, width: 1404 },
  });

  const heavy = result.nodes.find((node) => node.id === "taxonomy-1");
  const light = result.nodes.find((node) => node.id === "taxonomy-2");

  expect(distanceFromCenter(heavy!.position, { x: 702, y: 450 })).toBeLessThan(
    distanceFromCenter(light!.position, { x: 702, y: 450 }),
  );
});
```

- [ ] **Step 2: Run the focused layout test and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: FAIL until the branch solve goes beyond the placeholder radial layout.

- [ ] **Step 3: Implement the approved branch solve**

Implement in `buildBranchLayout.ts`:
- `bubbleDiameterFromDescendantCount(descendantCardCount)` using logarithmic scaling;
- deterministic ordering for the seed stage;
- center-out initial positions with multiple rings or spiraling offsets;
- short static `d3-force` solve using:
  - collision force;
  - weak center force;
  - weak radial or positional cohesion;
- post-solve normalization that keeps bubbles within the viewport padding;
- output mapping to React Flow node shape with branch-specific metadata and `targetNodeId`.

Avoid:
- continuous animation loops;
- hierarchy edge generation;
- random seeding that makes repeated entries visually unrelated;
- solving in React render instead of a dedicated helper.

- [ ] **Step 4: Re-run the layout test**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- branch layout now matches the approved floating weighted bubble field contract;
- heavy nodes prefer the center zone without collapsing into overlap;
- the spec remains synchronized with the implementation-facing behavior.

Avoided anti-patterns:
- No fake “force” implementation that is still a trivial polar loop.
- No silent clipping of overlapping bubbles instead of solving layout.
- No unnecessary general-purpose graph abstraction beyond branch needs.

Commit message shape:
- `[plan:2026-04-08-taxonomy-view-layouts-plan][task:T02] implement branch force layout`

## Chunk 2: Leaf Graph Layout and Page Integration

### Task T03: Implement static force-driven leaf layout with edge output

**Task ID:** `T03`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildLeafLayout.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Add failing leaf-layout tests for graph semantics**

Add tests that verify:
- leaf layout emits React Flow nodes and edges together;
- node labels stay title-first;
- `content` remains present in node data for hover disclosure;
- `inner` and `outer` do not force separate rings or separate coordinate bands;
- repeated solves with the same payload keep approximately stable rounded positions.

Include one test that uses a triangle or chain graph and asserts that all edge endpoints reference emitted node ids.

- [ ] **Step 2: Run the focused layout test and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: FAIL until leaf output includes a real edge mapping and force solve.

- [ ] **Step 3: Implement the approved leaf solve**

Implement in `buildLeafLayout.ts`:
- deterministic node seed ordering;
- static `d3-force` graph solve using:
  - link force;
  - collision force;
  - many-body separation;
  - weak center force;
- output mapping to React Flow nodes that keeps:
  - `label = title`;
  - `content` available for hover;
  - `scope` available for styling only;
- output mapping to React Flow edges derived from backend edge ids and endpoint ids.

Avoid:
- ring-based placement keyed by `inner` / `outer`;
- default visible content blocks inside nodes;
- silently dropping edges that fail to map; fail fast in tests and implementation if payload references unknown nodes.

- [ ] **Step 4: Re-run the layout test**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- leaf layout now produces both nodes and edges from the one-hop payload;
- default visible node content is title-only;
- `content` remains available for hover disclosure and the spec stays current.

Avoided anti-patterns:
- No fallback to branch-style bubble placement for leaf graphs.
- No silent edge omission.
- No forced `inner/outer` geometry that conflicts with the approved design.

Commit message shape:
- `[plan:2026-04-08-taxonomy-view-layouts-plan][task:T03] implement leaf force graph layout`

### Task T04: Integrate branch and leaf pipelines into the page while preserving the shell

**Task ID:** `T04`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/index.css`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-shell.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Extend the page test with failing integration expectations**

Add or update tests in `TaxonomyViewPage.test.tsx` so they fail until page integration is complete:

```tsx
it("renders branch bubbles from the branch layout pipeline", () => {
  renderWithRootChildren([
    { depth: 0, descendant_card_count: 50, id: 1, name: "Science" },
  ]);

  expect(screen.getByRole("button", { name: "Science" })).toBeInTheDocument();
});

it("renders leaf edges and title-first nodes", () => {
  renderWithLeafPayload({
    edges: [{ id: "e-1", source_node_id: 10, strength: 0.9, target_node_id: 11 }],
    nodes: [
      { content: "Inner content", id: 10, scope: "inner", title: "Inner node" },
      { content: "Outer content", id: 11, scope: "outer", title: "Outer node" },
    ],
  });

  expect(screen.getByText("Inner node")).toBeInTheDocument();
  expect(screen.queryByText("Inner content")).not.toBeInTheDocument();
  expect(screen.getByTestId("reactflow-edge-e-1")).toBeInTheDocument();
});
```

Update the local `@xyflow/react` mock so it can render supplied `edges` and expose deterministic edge test ids.

- [ ] **Step 2: Run the page test and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx
```

Expected: FAIL because the page still uses the shared radial helper and still passes `edges={[]}`.

- [ ] **Step 3: Integrate the approved page behavior**

Implement:
- extract node presentation into `TaxonomyFlowNode.tsx`;
- route root and branch payloads through `buildBranchLayout`;
- route leaf payloads through `buildLeafLayout`;
- pass real leaf edges into React Flow;
- keep branch click drill-down behavior through `targetNodeId`;
- expose `content` via hover disclosure on the custom node without adding permanent content panels;
- preserve the existing shell, breadcrumb overlay, loading overlay, and error overlay contracts.

Avoid:
- rebuilding the page shell or routing structure;
- recomputing force solves inside React Flow event handlers;
- using `title` HTML attributes as the only hover-disclosure mechanism if the node already has richer accessible hover UI available during implementation; prefer one consistent disclosure pattern.

- [ ] **Step 4: Re-run the page test**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- branch and leaf views now use separate layout pipelines inside the stable shell;
- leaf edges render in the page;
- leaf nodes stay title-first and reveal content on hover;
- shell behavior remains synchronized with both active design docs.

Avoided anti-patterns:
- No duplicated branch and leaf orchestration branches scattered across the page.
- No hidden fallback to empty edges.
- No workaround permanent content panel added outside the node hover flow.

Commit message shape:
- `[plan:2026-04-08-taxonomy-view-layouts-plan][task:T04] integrate branch and leaf layouts`

## Chunk 3: Visual Tuning and End-to-End Verification

### Task T05: Tune layout styling and complete verification evidence

**Task ID:** `T05`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/index.css`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-shell.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Add failing assertions for visual semantics that are testable in RTL**

Add assertions that verify:
- branch bubbles keep the branch affordance treatment;
- leaf nodes keep title-first markup and expose hover hooks;
- shell overlay hooks remain mounted while branch and leaf layouts switch.

- [ ] **Step 2: Run the focused page test and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx
```

Expected: FAIL until the final node styling and hover-disclosure hooks are in place.

- [ ] **Step 3: Implement CSS and interaction polish**

Implement:
- branch bubble styling that preserves the approved floating visual direction;
- leaf node styling that reads as title-first graph nodes rather than branch bubbles;
- hover-disclosure styling for `content`;
- any viewport padding or fit-view tuning needed so branch bubbles preserve breathing room and leaf nodes remain readable without changing shell height.

Avoid:
- changing the page-shell geometry;
- adding background treatments that override the approved default grid direction;
- using fragile CSS that depends on exact simulation coordinates.

- [ ] **Step 4: Run full verification**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx
pnpm run typecheck
pnpm exec biome check src/features/taxonomy-view/page/TaxonomyFlowNode.tsx src/features/taxonomy-view/page/TaxonomyViewPage.tsx src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx src/features/taxonomy-view/page/layout src/index.css
pnpm run build
```

Expected: PASS.

- [ ] **Step 4a: Perform browser-level evidence capture**

Confirm in browser or screenshot-driven inspection:
- branch view resembles the approved Figma branch bubble field and keeps visible breathing room;
- heavy branch bubbles read closer to the center zone than lighter ones;
- leaf view renders edges and title-first nodes without obvious overlap;
- hovering a leaf node reveals content without changing shell geometry;
- switching root -> branch -> leaf preserves the stable outer shell.

Record the evidence in the task notes when finalizing the task.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- styling now matches the approved branch and leaf behavior closely enough for implementation handoff acceptance;
- full verification evidence is recorded;
- all impacted spec files remain current and synchronized.

Avoided anti-patterns:
- No visual “fixes” that bypass the approved layout solves.
- No silent degradation from hover content to permanent visible content.
- No shell regression in exchange for layout polish.

Commit message shape:
- `[plan:2026-04-08-taxonomy-view-layouts-plan][task:T05] polish layout presentation and verify`

## Plan Coverage Gate

| Design commitment | Task IDs | Files | Tests / checks | Spec sync evidence |
| --- | --- | --- | --- | --- |
| Branch view is a floating bubble navigator, not a tree diagram | T01, T02, T04, T05 | `buildBranchLayout.ts`, `TaxonomyViewPage.tsx`, `TaxonomyFlowNode.tsx`, `index.css` | layout unit tests, page tests, browser inspection | `taxonomy-view-layouts.md` branch role and branch layout family |
| Branch bubble radius uses logarithmic scaling from `descendant_card_count` | T01, T02 | `buildBranchLayout.ts`, `taxonomyLayouts.test.ts` | layout unit tests | `taxonomy-view-layouts.md` branch size encoding |
| Branch layout uses seeded center-out static force settling | T02, T04 | `buildBranchLayout.ts`, `TaxonomyViewPage.tsx` | layout unit tests, page tests, browser inspection | `taxonomy-view-layouts.md` branch layout family |
| Branch view does not render hierarchy edges | T02, T04 | `buildBranchLayout.ts`, `TaxonomyViewPage.tsx` | layout unit tests, page tests | `taxonomy-view-layouts.md` branch view role |
| Leaf view renders one-hop nodes and edges together | T03, T04, T05 | `buildLeafLayout.ts`, `TaxonomyViewPage.tsx`, page tests | layout unit tests, page tests, browser inspection | `taxonomy-view-layouts.md` leaf view role |
| Leaf nodes are title-first and reveal content on hover | T03, T04, T05 | `buildLeafLayout.ts`, `TaxonomyFlowNode.tsx`, `index.css`, page tests | layout unit tests, page tests, browser inspection | `taxonomy-view-layouts.md` leaf node density rule |
| `inner` and `outer` do not impose geometry rules | T03 | `buildLeafLayout.ts`, `taxonomyLayouts.test.ts` | layout unit tests | `taxonomy-view-layouts.md` leaf scope handling |
| Branch and leaf layouts are deterministic and static per payload | T01, T02, T03 | layout helper files and tests | layout unit tests | `taxonomy-view-layouts.md` determinism rule |
| Stable shell geometry remains intact | T04, T05 | `TaxonomyViewPage.tsx`, `TaxonomyViewPage.test.tsx`, `index.css` | page tests, browser inspection, build | `taxonomy-view-shell.md` plus `taxonomy-view-layouts.md` shared canvas rule |
| No workaround-only, silent-failure, or unnecessary-duplication strategy | T01, T02, T03, T04, T05 | all modified files | task-level finalization checks | each task includes explicit anti-pattern avoidance and spec synchronization confirmation |

Coverage result:
- All approved behavior-changing layout deltas map to at least one task, file, test/check, and spec synchronization point.
- No task relies on workaround-only logic, silent failure, or unnecessary duplication as the default strategy.
- Each task has exactly one controller-owned finalization step.

Plan complete and saved to `/Users/mianqin/Code/knowledge/.orbital/specs/plans/2026-04-08-taxonomy-view-layouts-plan.md`. Ready to execute?
