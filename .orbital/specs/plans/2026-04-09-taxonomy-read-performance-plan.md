---
abstract: Implementation plan for reducing taxonomy root and leaf read latency by replacing broad scans with indexed, scoped queries.
out_of_scope: Frontend visual redesign, taxonomy contract shape changes, and semantic ranking policy.
---

# Taxonomy Read Performance Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-04-09-taxonomy-read-performance-plan`

**Goal:** Reduce taxonomy browsing latency by adding the missing assignment access path, scoping leaf membership reads to one leaf, using adjacency-driven leaf edge expansion, and making leaf detail hydration fetch only the requested node details.

**Architecture:** Keep the external taxonomy HTTP contracts unchanged and fix the backend read model behind them. The repository layer gains indexed, leaf-scoped read primitives; the service layer stops using full-assignment and full-detail work for leaf-specific requests; migrations add the missing database index needed for leaf membership lookups. Verification covers correctness and query freshness, then uses database `EXPLAIN` output or response-time checks to confirm the intended access pattern.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

**Assumptions and Constraints:**
- Taxonomy HTTP response shapes stay unchanged in this round.
- Branch and leaf frontend behavior stays unchanged in this round.
- Database engine remains PostgreSQL with Alembic-managed schema.
- Query improvements must address root cause; caching is out of scope for this round.
- Migrations must be additive and safe for existing local/dev data.

**Decision Gates:** None open. The accepted design already commits to scoped leaf reads and adjacency-driven edge expansion.

**Tech Stack:**
- FastAPI + Pydantic v2
- SQLAlchemy async ORM
- Alembic
- PostgreSQL
- Pytest

---

## File Structure Map

### Schema and migration
- Create: `/Users/mianqin/Code/knowledge/apps/api/alembic/versions/2026_04_09_add_taxonomy_assignment_lookup_indexes_<revision>.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/model.py`

### Repository and service
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/repo.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/ports.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/service.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/knowledge_graph/repo.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/knowledge_graph/ports.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/knowledge_graph/service.py`

### Tests
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_repo.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_service.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/knowledge_graph/test_repo.py`

### Spec synchronization
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

### Structure rationale
- The current leaf path mixes whole-table membership reads, broad edge scans, and whole-graph detail reads into one request path. That pattern directly conflicts with the accepted performance design.
- This plan separates concerns into:
  - database access paths for assignment membership;
  - leaf-scoped taxonomy repository reads;
  - adjacency-driven knowledge-graph edge expansion;
  - requested-node-only detail hydration.

## Chunk 1: Index and Repository Access Paths

### Task T01: Add the missing assignment lookup indexes and expose leaf-scoped membership reads

**Task ID:** `T01`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/apps/api/alembic/versions/2026_04_09_add_taxonomy_assignment_lookup_indexes_<revision>.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/model.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/repo.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/ports.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_repo.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`

- [ ] **Step 1: Write the failing repository tests**

Add tests that require:
- the SQLAlchemy model metadata to expose indexes covering `taxonomy_node_id` and `(taxonomy_node_id, node_id)` on `node_taxonomy_assignments`;
- a repository method that returns only the `node_id` values assigned to one taxonomy leaf, ordered by `node_id ASC`;
- leaf-scoped reads to avoid returning assignments for other leaves.

- [ ] **Step 2: Run the focused repository tests and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_repo.py -q
```

Expected: FAIL because the new indexes and leaf-scoped repository method do not exist yet.

- [ ] **Step 3: Implement the migration, model metadata, and repository method**

Implement:
- Alembic migration that creates:
  - an index on `node_taxonomy_assignments.taxonomy_node_id`
  - an index on `(taxonomy_node_id, node_id)`
- SQLAlchemy model metadata that reflects the same indexes
- repository/port method:
  - `list_assigned_node_ids_for_leaf(leaf_id: int) -> list[int]`

Avoid:
- replacing the existing unique constraint on `node_id`;
- broad repository helpers that still expose whole-assignment reads to leaf-specific call sites;
- hidden ordering assumptions.

- [ ] **Step 4: Re-run the focused repository tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_repo.py -q
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- the migration and model metadata describe the accepted lookup indexes;
- leaf-scoped assignment reads exist and are ordered deterministically;
- related spec files remain current and synchronized.

Avoided anti-patterns:
- No cache-first workaround.
- No migration that drops or rewrites existing assignment data.
- No new repository method that still returns all assignments and leaves filtering to callers.

Commit message shape:
- `[plan:2026-04-09-taxonomy-read-performance-plan][task:T01] add assignment lookup indexes`

## Chunk 2: Adjacency-Driven Leaf Graph Expansion

### Task T02: Replace broad leaf edge scans with adjacency-driven edge expansion

**Task ID:** `T02`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/knowledge_graph/repo.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/knowledge_graph/ports.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/knowledge_graph/service.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/knowledge_graph/test_repo.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/service.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`

- [ ] **Step 1: Write the failing tests**

Add tests that require:
- leaf edge expansion to use adjacency-driven access semantics;
- the returned edge set to stay identical to the current one-hop contract;
- the taxonomy service leaf graph path to call the new adjacency-driven repository method instead of the broad edge scan.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/knowledge_graph/test_repo.py apps/api/tests/unit/modules/taxonomy/test_service.py -q
```

Expected: FAIL because the old broad edge query is still active.

- [ ] **Step 3: Implement adjacency-driven edge expansion**

Implement:
- a knowledge-graph repository/port method that:
  - starts from `adjacency.node_id`
  - resolves `edge_id`
  - joins to `edges`
  - returns deduplicated canonical edge pairs touching the supplied node ids
- taxonomy service leaf graph expansion updated to use the new method

Avoid:
- retaining the old `edges WHERE node_a_id IN (...) OR node_b_id IN (...)` scan in the active leaf path;
- changing the external edge contract or ordering;
- duplicate edges caused by multiple adjacency matches.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/knowledge_graph/test_repo.py apps/api/tests/unit/modules/taxonomy/test_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- leaf edge expansion uses adjacency-driven access;
- output semantics stay unchanged;
- related specs remain current and synchronized.

Avoided anti-patterns:
- No fallback path that silently keeps the old broad scan in production code.
- No query rewrite that changes one-hop graph semantics.

Commit message shape:
- `[plan:2026-04-09-taxonomy-read-performance-plan][task:T02] use adjacency for leaf edges`

## Chunk 3: Requested-Node-Only Leaf Details

### Task T03: Make leaf detail hydration validate membership without loading whole-graph details

**Task ID:** `T03`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/service.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/repo.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/ports.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_service.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Write the failing service tests**

Add tests that require:
- `get_leaf_node_details()` to validate requested ids against the active one-hop graph membership set;
- `get_leaf_node_details()` to fetch `title/content` only for requested node ids after validation;
- no whole-graph `title/content` load in the active detail path.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_service.py -q
```

Expected: FAIL because the current detail path still builds whole-graph node details.

- [ ] **Step 3: Implement requested-node-only detail hydration**

Implement:
- a service split between:
  - one-hop membership validation
  - requested-node detail fetch
- reuse of the new leaf-scoped assignment read for inner-node membership
- requested-node-only detail lookup after validation succeeds

Avoid:
- loading `title/content` for every node in the expanded one-hop graph;
- weakening validation rules;
- adding silent partial success for invalid node ids.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- leaf detail hydration only reads requested node details;
- membership validation still matches the active one-hop graph;
- related specs remain current and synchronized.

Avoided anti-patterns:
- No behavior change to the external detail contract.
- No hidden fallback that loads the whole graph “just in case.”

Commit message shape:
- `[plan:2026-04-09-taxonomy-read-performance-plan][task:T03] scope leaf detail reads`

## Chunk 4: Full Verification and Evidence

### Task T04: Verify correctness, contract freshness, and query-shape improvements end to end

**Task ID:** `T04`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy-view-layouts.md`

- [ ] **Step 1: Add failing or missing verification checks**

Add any remaining targeted assertions needed to prove:
- leaf-scoped assignment reads stay ordered and isolated;
- adjacency-driven edge expansion preserves one-hop graph semantics;
- detail hydration does not fetch whole-graph details.

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /Users/mianqin/Code/knowledge
uv run pytest apps/api/tests/unit/modules/taxonomy/test_repo.py apps/api/tests/unit/modules/taxonomy/test_service.py apps/api/tests/unit/modules/taxonomy/test_api.py apps/api/tests/unit/modules/knowledge_graph/test_repo.py -q
```

Then collect evidence with PostgreSQL against the running dev database:

```bash
cd /Users/mianqin/Code/knowledge
docker exec knowledge-postgres-1 psql -U knowledge_admin -d knowledge -c "SELECT tablename, indexname FROM pg_indexes WHERE schemaname='public' AND tablename IN ('node_taxonomy_assignments');"
docker exec knowledge-postgres-1 psql -U knowledge_admin -d knowledge -c \"EXPLAIN ANALYZE SELECT node_id FROM node_taxonomy_assignments WHERE taxonomy_node_id = <leaf_id> ORDER BY node_id ASC;\"
docker exec knowledge-postgres-1 psql -U knowledge_admin -d knowledge -c \"EXPLAIN ANALYZE <adjacency-driven leaf edge query for a representative leaf_id>;\"
```

Expected:
- all tests PASS;
- index metadata is present;
- the representative plans show leaf-scoped assignment lookup and adjacency-driven edge access rather than broad edge scanning.

- [ ] **Step 3: Controller finalizes task**

Confirm:
- behavior and contracts are unchanged from the client’s point of view;
- the accepted read-performance fixes are implemented behind the existing API;
- active spec files remain synchronized with the accepted current truth.

Avoided anti-patterns:
- No fake performance claim without query evidence.
- No stale spec text after behavior-changing backend work.
- No cache layer introduced as a substitute for query-shape fixes.

Commit message shape:
- `[plan:2026-04-09-taxonomy-read-performance-plan][task:T04] verify taxonomy read performance`

---

## Plan Coverage Gate

| Design commitment | Task IDs | Files | Tests/Checks | Spec updates |
| --- | --- | --- | --- | --- |
| Leaf-specific reads use leaf-scoped assignment lookup instead of whole-assignment scans | T01, T03, T04 | `taxonomy/model.py`, `taxonomy/repo.py`, `taxonomy/ports.py`, `taxonomy/service.py`, Alembic migration | `test_repo.py`, `test_service.py`, PostgreSQL `EXPLAIN` for `taxonomy_node_id` lookup | `taxonomy.md` |
| Leaf edge expansion uses adjacency-driven access instead of broad edge scanning | T02, T04 | `knowledge_graph/repo.py`, `knowledge_graph/ports.py`, `knowledge_graph/service.py`, `taxonomy/service.py` | `knowledge_graph/test_repo.py`, `taxonomy/test_service.py`, PostgreSQL `EXPLAIN` for adjacency-driven edge query | `taxonomy.md` |
| Leaf detail hydration fetches only requested node details after validation | T03, T04 | `taxonomy/service.py`, `taxonomy/repo.py`, `taxonomy/ports.py` | `taxonomy/test_service.py` | `taxonomy.md`, `taxonomy-view-layouts.md` |
| Frontend LOD assumptions stay valid because backend detail path remains bounded | T03, T04 | `taxonomy/service.py` | service tests plus representative DB evidence | `taxonomy-view-layouts.md` |
| External HTTP contracts remain unchanged while backend read model improves | T01, T02, T03, T04 | taxonomy repo/service and knowledge-graph repo/service files | `taxonomy/test_api.py`, focused backend tests | `taxonomy.md` |

Coverage verdict:
- Every accepted performance commitment is mapped to code, tests, and spec updates.
- No task relies on caching or hidden fallback behavior as the primary strategy.
- Each task has exactly one controller-owned finalization step at task end.

Plan complete and saved to `/Users/mianqin/Code/knowledge/.orbital/specs/plans/2026-04-09-taxonomy-read-performance-plan.md`. Ready to execute?
