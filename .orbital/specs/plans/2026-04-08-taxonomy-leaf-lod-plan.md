---
abstract: Implementation plan for converting taxonomy leaf browsing into a level-of-detail graph with skeleton-first loading and viewport-scoped detail hydration.
out_of_scope: Branch bubble behavior, taxonomy classification flows, and page-shell chrome redesign.
---

# Taxonomy Leaf LOD Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-04-08-taxonomy-leaf-lod-plan`

**Goal:** Replace the current all-at-once leaf graph with a two-stage leaf browser that enters in point mode, delays title/content loading until zoom activation, and hydrates only viewport-scoped nodes plus overscan.

**Architecture:** Split leaf browsing into a backend skeleton surface and a backend detail surface. The frontend keeps one stable force-solved leaf skeleton graph, derives point mode versus bubble mode from zoom, and hydrates node details in batched viewport-scoped requests cached per active leaf.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-shell.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

**Assumptions and Constraints:**
- Branch behavior is unchanged in this round.
- Leaf layout geometry continues to come from the existing static `d3-force` solve.
- Entering a leaf must not request node `title` or `content`.
- Leaf detail hydration is batch-based and keyed by explicit node ids for one active leaf.
- Bubble rendering is gated by one explicit zoom threshold and viewport plus overscan coverage.
- Hydrated details are cached for the active leaf and reused during subsequent pan/zoom events.
- Contracts generated under `/Users/mianqin/Code/knowledge/packages/contracts/` must stay synchronized with backend schema changes.

**Decision Gates:** None open. The approved design already commits to skeleton-first leaf loading, point-mode overview, and viewport-scoped bubble hydration.

**Tech Stack:**
- FastAPI + Pydantic v2
- React 19 + TypeScript
- TanStack Query
- React Flow
- `d3-force`
- Vitest + React Testing Library
- OpenAPI export + generated contract types

---

## File Structure Map

### Backend taxonomy contract and service
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/api.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/schema.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/service.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_api.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_service.py`

### Contract generation
- Modify: `/Users/mianqin/Code/knowledge/packages/contracts/openapi/openapi.json`
- Modify: `/Users/mianqin/Code/knowledge/packages/contracts/generated/types.ts`
- Modify: `/Users/mianqin/Code/knowledge/packages/contracts/generated/client.ts`

### Frontend data/query and LOD state
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayoutTypes.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildLeafLayout.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.test.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx`

### Spec synchronization
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

### Structure rationale
- The current leaf path couples topology, title rendering, and content hydration into one payload and one render mode. That pattern directly conflicts with the approved LOD browsing model.
- This plan separates concerns into:
  - backend leaf skeleton contract;
  - backend leaf detail hydration contract;
  - frontend point-mode graph;
  - frontend viewport-scoped bubble upgrade logic.
- The split is limited to behavior required by the approved design and avoids unrelated refactoring.

## Chunk 1: Backend Skeleton and Detail Contracts

### Task T01: Replace the leaf node-view payload with a skeleton contract and add a detail-hydration endpoint

**Task ID:** `T01`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/schema.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/api.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/service.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_api.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_service.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`

- [ ] **Step 1: Write the failing backend tests**

Add tests that verify:
- `GET /taxonomy/view/nodes/{leaf_id}` returns leaf `nodes` with only `id` and `scope`, plus `edges`;
- the leaf node-view response does not include `title` or `content`;
- `POST /taxonomy/view/leaves/{leaf_id}/details` accepts `node_ids` and returns ordered `id/title/content` records;
- the details route rejects empty arrays, duplicate ids, non-leaf taxonomy ids, and node ids outside the active one-hop leaf graph.

Example assertion shape:

```py
response = await async_client.get("/taxonomy/view/nodes/2")
payload = response.json()

assert payload["node_kind"] == "leaf"
assert payload["nodes"] == [
    {"id": 11, "scope": "inner"},
    {"id": 12, "scope": "outer"},
]
```

- [ ] **Step 2: Run the focused backend tests and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_service.py apps/api/tests/unit/modules/taxonomy/test_api.py -q
```

Expected: FAIL because the current backend still returns full leaf node payloads and has no details endpoint.

- [ ] **Step 3: Implement the schema, service, and route split**

Implement:
- skeleton-only leaf node response models in `schema.py`;
- detail request/response models in `schema.py`;
- service methods that:
  - return one-hop skeleton nodes and edges for leaf node view;
  - validate requested ids against the active leaf graph and return ordered detail records;
- API wiring in `api.py` for `POST /taxonomy/view/leaves/{node_id}/details`.

Avoid:
- embedding `title/content` back into the skeleton response;
- silently dropping unknown or out-of-scope node ids;
- duplicating one-hop graph construction logic between skeleton and detail paths when one shared internal helper can own it.

- [ ] **Step 4: Re-run the focused backend tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_service.py apps/api/tests/unit/modules/taxonomy/test_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- leaf node view now returns only skeleton data;
- leaf details are fetched through the dedicated route with validation;
- related spec files remain current and synchronized.

Avoided anti-patterns:
- No workaround that leaves the old full leaf payload available as the active contract.
- No silent partial success for invalid detail requests.
- No branch behavior changes folded into this task.

Commit message shape:
- `[plan:2026-04-08-taxonomy-leaf-lod-plan][task:T01] split leaf skeleton and detail contracts`

## Chunk 2: Contracts and Frontend Query Boundary

### Task T02: Regenerate contracts and introduce frontend query helpers for leaf detail hydration

**Task ID:** `T02`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/packages/contracts/openapi/openapi.json`
- Modify: `/Users/mianqin/Code/knowledge/packages/contracts/generated/types.ts`
- Modify: `/Users/mianqin/Code/knowledge/packages/contracts/generated/client.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayoutTypes.ts`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Write the failing frontend query tests or type assertions**

Extend existing page/query tests or add focused type-level checks that require:
- the leaf node-view query type to expose skeleton nodes without `title/content`;
- a new detail-query helper that accepts `(leafId, nodeIds[])` and returns ordered detail records;
- frontend leaf layout types to support point-mode nodes and hydrated leaf bubble nodes separately.

- [ ] **Step 2: Run the focused frontend tests/checks and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
pnpm run typecheck
```

Expected: FAIL because the generated contracts and query helpers still assume full leaf payloads.

- [ ] **Step 3: Regenerate contracts and implement query helpers**

Implement:
- regenerated OpenAPI and generated client/types artifacts;
- a new frontend detail-query helper in `taxonomyViewQueries.ts`;
- query-key structure that distinguishes:
  - root view;
  - node view;
  - leaf detail batches by `(leafId, sortedNodeIds)`;
- layout types that distinguish skeleton leaf node metadata from hydrated title/content detail records.

Avoid:
- hand-editing generated files without regenerating from OpenAPI;
- using ad hoc `fetch` instead of the contracts client;
- leaking detail payload assumptions into branch paths.

- [ ] **Step 4: Re-run the focused frontend tests/checks**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
pnpm run typecheck
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- generated contracts are synchronized with backend schema;
- frontend query helpers can request leaf details in batches;
- related design specs remain current and synchronized.

Avoided anti-patterns:
- No shadow contract types maintained only in the frontend.
- No workaround that keeps using stale generated artifacts.
- No leaf detail requests outside the contracts client boundary.

Commit message shape:
- `[plan:2026-04-08-taxonomy-leaf-lod-plan][task:T02] add leaf detail query boundary`

## Chunk 3: Leaf Point Mode and Viewport Hydration

### Task T03: Convert leaf rendering to point-mode overview with zoom-gated bubble hydration

**Task ID:** `T03`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/buildLeafLayout.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyFlowNode.test.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Write the failing LOD behavior tests**

Add tests that verify:
- entering a leaf renders point-mode nodes without visible titles;
- below the zoom threshold, no leaf detail query is issued;
- at or above the zoom threshold, only viewport plus overscan node ids are requested for hydration;
- hydrated viewport nodes render as bubbles with titles, while offscreen nodes remain points;
- hover disclosure appears only for hydrated bubble nodes with cached content.

Example assertion shape:

```tsx
expect(screen.queryByText("Inner node")).not.toBeInTheDocument();
expect(fetchLeafDetailsMock).not.toHaveBeenCalled();
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyFlowNode.test.tsx src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: FAIL because the current leaf path still renders title-first bubbles from the initial payload.

- [ ] **Step 3: Implement point-mode rendering and hydration orchestration**

Implement:
- leaf layout output that can support point-mode nodes with stable geometry and lightweight visual markers;
- page-level viewport tracking and one explicit `bubbleActivationZoom` threshold;
- overscan-based node-id selection for hydration requests;
- active-leaf detail cache keyed by node id;
- bubble upgrade only for hydrated nodes inside viewport plus overscan;
- point-mode fallback for all other leaf nodes.

Avoid:
- requesting details before the threshold is reached;
- upgrading the entire leaf graph to bubbles at once;
- storing duplicated mutable truth for point versus bubble nodes when it can be derived from viewport, zoom, and cache;
- hiding loading failures with silent empty-title fallbacks.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyFlowNode.test.tsx src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- leaf entry is skeleton-first and point-mode by default;
- bubble hydration is zoom-gated and viewport-scoped;
- hover disclosure depends on hydrated content rather than initial payload shape;
- related specs remain current and synchronized.

Avoided anti-patterns:
- No all-or-nothing bubble switch for the entire graph.
- No repeated refetching of already cached node details during pan/zoom.
- No branch-path regressions introduced through shared node rendering.

Commit message shape:
- `[plan:2026-04-08-taxonomy-leaf-lod-plan][task:T03] implement leaf point-mode hydration`

## Chunk 4: Overscan, Verification, and Freshness

### Task T04: Finalize overscan behavior, browser verification, and full-stack contract freshness

**Task ID:** `T04`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
- Modify: `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx`
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Add failing verification-oriented tests for overscan reuse**

Add targeted tests that verify:
- panning inside bubble mode requests only newly entered overscan nodes;
- already hydrated nodes are not re-requested;
- leaving the viewport can downgrade nodes back to points without clearing their cached details.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx
```

Expected: FAIL until overscan reuse and cache retention are explicitly wired.

- [ ] **Step 3: Implement overscan reuse and run full verification**

Implement any remaining viewport-selection or cache-reuse fixes, then run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_service.py apps/api/tests/unit/modules/taxonomy/test_api.py -q
pnpm --dir packages/contracts run verify
cd /Users/mianqin/Code/knowledge/apps/web
pnpm exec vitest --run src/features/taxonomy-view/page/TaxonomyFlowNode.test.tsx src/features/taxonomy-view/page/TaxonomyViewPage.test.tsx src/features/taxonomy-view/page/layout/taxonomyLayouts.test.ts
pnpm run typecheck
pnpm run build
```

Also perform browser-level verification against the running dev stack to confirm:
- entering a leaf shows points with no titles;
- crossing the zoom threshold hydrates only local nodes into bubbles;
- panning continues to hydrate new local nodes without turning the whole graph into bubbles.

- [ ] **Step 4: Controller finalizes task**

Confirm:
- overscan reuse behavior is implemented and verified;
- contracts and generated artifacts are current;
- active spec files remain synchronized with the accepted LOD behavior.

Avoided anti-patterns:
- No fake verification based only on unit tests when browser behavior is central to the feature.
- No stale contract artifacts left after backend schema changes.
- No cache eviction churn without a demonstrated need.

Commit message shape:
- `[plan:2026-04-08-taxonomy-leaf-lod-plan][task:T04] finalize leaf lod verification`

---

## Plan Coverage Gate

| Design commitment | Task IDs | Files | Tests/Checks | Spec updates |
| --- | --- | --- | --- | --- |
| Leaf node view returns skeleton only on entry | T01, T02 | `apps/api/src/modules/taxonomy/schema.py`, `apps/api/src/modules/taxonomy/api.py`, `apps/api/src/modules/taxonomy/service.py`, `apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.ts` | `uv run pytest apps/api/tests/unit/modules/taxonomy/test_service.py apps/api/tests/unit/modules/taxonomy/test_api.py -q`, `pnpm run typecheck` | `taxonomy.md`, `taxonomy-view-layouts.md` |
| Leaf details are fetched by explicit node-id batches | T01, T02 | `apps/api/src/modules/taxonomy/*`, `apps/web/src/features/taxonomy-view/data/taxonomyViewQueries.ts` | backend unit tests, contract verification, frontend typecheck | `taxonomy.md`, `taxonomy-view-layouts.md` |
| Leaf enters in point mode with no visible titles/content | T03 | `buildLeafLayout.ts`, `TaxonomyFlowNode.tsx`, `TaxonomyViewPage.tsx` | `pnpm exec vitest --run ...TaxonomyFlowNode.test.tsx ...TaxonomyViewPage.test.tsx ...taxonomyLayouts.test.ts` | `taxonomy-view-layouts.md` |
| Bubble mode is gated by zoom threshold and viewport plus overscan | T03, T04 | `TaxonomyViewPage.tsx`, `TaxonomyViewPage.test.tsx` | focused vitest runs and browser verification | `taxonomy-view-layouts.md` |
| Hydrated details are cached and reused during pan/zoom | T03, T04 | `TaxonomyViewPage.tsx`, `TaxonomyViewPage.test.tsx` | focused vitest runs and browser verification | `taxonomy-view-layouts.md` |
| Contracts remain synchronized with API behavior | T02, T04 | `packages/contracts/openapi/openapi.json`, `packages/contracts/generated/types.ts`, `packages/contracts/generated/client.ts` | `pnpm --dir packages/contracts run verify` | `taxonomy.md` |

Coverage verdict:
- Every approved behavior-changing delta is mapped to backend, frontend, verification, and spec synchronization work.
- No task relies on workaround-only behavior, silent failure, or defensive masking of invalid requests.
- Each task has exactly one controller-owned finalization step at task end.

Plan complete and saved to `/Users/mianqin/Code/knowledge/.orbital/specs/plans/2026-04-08-taxonomy-leaf-lod-plan.md`. Ready to execute?
