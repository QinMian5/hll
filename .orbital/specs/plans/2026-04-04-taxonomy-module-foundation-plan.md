---
abstract: Implementation plan for the taxonomy module foundation covering LCC tree persistence, final leaf assignment truth, and bootstrap import flow.
out_of_scope: LLM classification orchestration, candidate/confidence workflows, semantic-map consumption changes, and frontend taxonomy rendering.
---

# Taxonomy Module Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-04-04-taxonomy-module-foundation-plan`

**Goal:** Build the backend `taxonomy` module that persists the authoritative LCC tree, stores one final leaf assignment per knowledge node, and imports taxonomy data through a dedicated operator script.

**Architecture:** The implementation adds a dedicated `apps/api/src/modules/taxonomy` module with isolated persistence, repository/service boundaries, and a bootstrap-only import path from `human_workspace/LCC.yaml`. Knowledge nodes remain owned by `knowledge_graph`; taxonomy truth lives in its own tables and is linked through foreign keys plus a database trigger that enforces leaf-only assignments.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/00-system-definition.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/01-system-modules.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/08-persistence-schema-projection.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/10-migration-lifecycle-governance.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-ingestion-search-orchestration.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`

**Assumptions and Constraints:**
- `knowledge_graph` persistence stays unchanged; taxonomy truth is isolated in dedicated tables.
- LCC is treated as one authoritative, effectively stable tree with no versioning or merge/update import behavior.
- Each knowledge node can bind to exactly one final taxonomy leaf.
- Taxonomy import is bootstrap-only and MUST fail when taxonomy storage already contains rows.
- Table/column/index schema changes use ORM metadata plus governed Alembic autogenerate where possible.
- The leaf-only assignment trigger uses one dedicated hand-authored migration that contains only trigger/function DDL.
- This plan does not introduce HTTP taxonomy endpoints, semantic-map rebuild rewiring, or any LLM-based classification workflow.
- The implementation MUST avoid hidden fallback behavior, silent import skipping, or duplicate config entrypoints.
- Task execution does not auto-create Git commits; commits happen only on explicit human instruction.

**Decision Gates:** None open. The trigger migration exception is resolved: keep ORM/autogenerate for schema projection and use one dedicated manual migration only for the leaf-only trigger.

**Tech Stack:**
- Backend: Python 3.14, SQLAlchemy 2, Alembic, PostgreSQL
- Import/bootstrap: PyYAML, governed repository scripts
- Validation: pytest, Ruff, Ty, import-linter

---

## File Structure Map

### Taxonomy module
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/__init__.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/dto.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/errors.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/model.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/repo.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/service.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/ports.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/importer.py`

### Backend integration points
- Modify: `/Users/mianqin/Code/knowledge/apps/api/alembic/env.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/pyproject.toml`
- Create: `/Users/mianqin/Code/knowledge/apps/api/alembic/versions/<timestamp>_add_taxonomy_tables.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/alembic/versions/<timestamp>_add_taxonomy_leaf_assignment_trigger.py`
- Create: `/Users/mianqin/Code/knowledge/scripts/taxonomy-import-lcc.py`

### Tests
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/__init__.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_model_projection.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_repo.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_service.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_importer.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/integration/test_taxonomy_import_flow.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/integration/test_taxonomy_assignment_trigger.py`

### Spec synchronization
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/08-persistence-schema-projection.md` only if implementation reveals a schema detail that differs from the accepted current truth.
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/10-migration-lifecycle-governance.md` only if implementation reveals a migration-governance detail that differs from the accepted current truth.
- Modify: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md` only if implementation reveals an accepted behavior delta from the approved design.

---

## Chunk 1: Persistence Truth

### Task T01: Add taxonomy table projection and register schema metadata

**Task ID:** `T01`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/__init__.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/model.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/alembic/env.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/alembic/versions/<timestamp>_add_taxonomy_tables.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/__init__.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_model_projection.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/08-persistence-schema-projection.md`

- [ ] **Step 1: Write the failing model-projection test**

```python
def test_taxonomy_nodes_projection_contains_parent_depth_and_leaf_flag() -> None:
    table = TaxonomyNodeModel.__table__
    assert "parent_id" in table.c
    assert "depth" in table.c
    assert "is_leaf" in table.c
```

```python
def test_node_taxonomy_assignments_projection_contains_unique_node_constraint() -> None:
    table = NodeTaxonomyAssignmentModel.__table__
    unique_column_sets = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("node_id",) in unique_column_sets
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/unit/modules/taxonomy/test_model_projection.py -v
```

Expected: FAIL because the taxonomy module and table projection do not exist.

- [ ] **Step 3: Implement the minimal table projection**

Implement:
- `taxonomy_nodes` with `id`, `parent_id`, `name`, `depth`, `is_leaf`, and uniqueness over `(parent_id, name)`
- `node_taxonomy_assignments` with `id`, `node_id`, `taxonomy_node_id`, `assigned_at`, and uniqueness over `node_id`
- Alembic metadata registration for the taxonomy ORM model
- one governed autogenerate revision for tables/constraints/indexes only

Avoid:
- adding workflow-state columns (`status`, `confidence`, `candidate_*`)
- introducing external stable keys or YAML-derived codes
- mutating `knowledge_graph` tables
- embedding trigger SQL into the autogenerate table migration

- [ ] **Step 4: Run the targeted test and metadata checks**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/unit/modules/taxonomy/test_model_projection.py -v
ty check src/modules/taxonomy tests/unit/modules/taxonomy alembic/env.py
uvx ruff check src/modules/taxonomy tests/unit/modules/taxonomy alembic/env.py
```

Expected: PASS

- [ ] **Step 5: Controller finalizes task**

Confirm:
- Targeted projection tests and static checks pass
- The table migration is autogenerate-derived and contains only schema projection for taxonomy tables
- Related spec files remain current and synchronized with the accepted taxonomy persistence truth

### Task T02: Add the dedicated leaf-only assignment trigger migration

**Task ID:** `T02`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/apps/api/alembic/versions/<timestamp>_add_taxonomy_leaf_assignment_trigger.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/integration/test_taxonomy_assignment_trigger.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/10-migration-lifecycle-governance.md`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`

- [ ] **Step 1: Write the failing trigger-behavior test**

```python
@pytest.mark.anyio
async def test_assignment_to_non_leaf_taxonomy_node_is_rejected(async_session: AsyncSession) -> None:
    parent = await insert_taxonomy_node(async_session, name="Science", depth=0, is_leaf=False)
    node_id = await insert_knowledge_node(async_session)

    with pytest.raises(Exception):
        await insert_taxonomy_assignment(
            async_session,
            node_id=node_id,
            taxonomy_node_id=parent.id,
        )
```

- [ ] **Step 2: Run the trigger test to verify it fails**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/integration/test_taxonomy_assignment_trigger.py -v
```

Expected: FAIL because the trigger does not exist yet.

- [ ] **Step 3: Add one dedicated hand-authored trigger migration**

Implement:
- one hand-authored Alembic revision containing only:
  - the trigger function
  - the trigger DDL for `node_taxonomy_assignments`
- no unrelated table or column changes in this revision

Avoid:
- application-layer-only enforcement
- mixing trigger DDL with unrelated autogenerate deltas
- swallowing trigger failures behind fallback behavior

- [ ] **Step 4: Run the integration test to verify the trigger works**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/integration/test_taxonomy_assignment_trigger.py -v
```

Expected: PASS with non-leaf assignment rejected and leaf assignment accepted.

- [ ] **Step 5: Controller finalizes task**

Confirm:
- The trigger revision is isolated to leaf-only enforcement
- Integration evidence proves non-leaf assignments are rejected at the database boundary
- Related spec files remain current and synchronized with the accepted trigger-governance decision

---

## Chunk 2: Import Bootstrap

### Task T03: Add taxonomy importer and bootstrap script

**Task ID:** `T03`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/dto.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/errors.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/importer.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/ports.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/repo.py`
- Create: `/Users/mianqin/Code/knowledge/scripts/taxonomy-import-lcc.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_importer.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/integration/test_taxonomy_import_flow.py`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/taxonomy.md`

- [ ] **Step 1: Write failing tests for bootstrap-only import**

```python
def test_importer_builds_depth_and_leaf_flags_from_yaml_tree() -> None:
    nodes = import_taxonomy_tree(sample_lcc_yaml())
    assert any(node.depth == 0 for node in nodes)
    assert any(node.is_leaf for node in nodes)
```

```python
@pytest.mark.anyio
async def test_importer_fails_when_taxonomy_store_is_not_empty() -> None:
    await seed_one_taxonomy_row(async_session)
    with pytest.raises(TaxonomyImportError, match="already contains"):
        await run_import(async_session)
```

- [ ] **Step 2: Run the targeted import tests to verify they fail**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/unit/modules/taxonomy/test_importer.py tests/integration/test_taxonomy_import_flow.py -v
```

Expected: FAIL because importer code and bootstrap script do not exist.

- [ ] **Step 3: Implement the bootstrap-only importer**

Implement:
- YAML tree parsing from `human_workspace/LCC.yaml`
- deterministic depth computation
- deterministic `is_leaf` computation
- import guard that fails when taxonomy storage is non-empty
- one operator script that runs the import explicitly and does not auto-run in migrations or app startup

Avoid:
- merge/update reconciliation
- fallback to partial import on malformed or duplicate input
- storing YAML parsing details outside the taxonomy module
- adding hidden config sources for the import path

- [ ] **Step 4: Run the import tests and script-level checks**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/unit/modules/taxonomy/test_importer.py tests/integration/test_taxonomy_import_flow.py -v
ty check src/modules/taxonomy tests/unit/modules/taxonomy tests/integration/test_taxonomy_import_flow.py
uvx ruff check src/modules/taxonomy tests/unit/modules/taxonomy tests/integration/test_taxonomy_import_flow.py
```

Expected: PASS

- [ ] **Step 5: Controller finalizes task**

Confirm:
- Import fails cleanly when taxonomy storage is non-empty
- Import produces correct `depth` and `is_leaf` values
- The bootstrap script is the only accepted taxonomy import entrypoint
- Related spec files remain current and synchronized with the accepted import boundary

---

## Chunk 3: Read/Write Module Boundaries

### Task T04: Add taxonomy repository/service boundaries for tree reads and final assignments

**Task ID:** `T04`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/repo.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/service.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_repo.py`
- Create: `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_service.py`
- Modify: `/Users/mianqin/Code/knowledge/apps/api/pyproject.toml` if import-linter rules are needed for `semantic_map -> taxonomy service ports only`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/01-system-modules.md`
- Spec: `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`

- [ ] **Step 1: Write failing tests for accepted taxonomy reads**

```python
@pytest.mark.anyio
async def test_repo_returns_children_ordered_by_name(async_session: AsyncSession) -> None:
    parent_id = await seed_parent(async_session)
    await seed_child(async_session, parent_id=parent_id, name="Physics")
    await seed_child(async_session, parent_id=parent_id, name="Chemistry")

    repo = TaxonomyRepo(session=async_session)
    children = await repo.list_children(parent_id=parent_id)

    assert [child.name for child in children] == ["Chemistry", "Physics"]
```

```python
@pytest.mark.anyio
async def test_service_returns_final_leaf_assignment_for_node() -> None:
    assignment = await service.get_assignment_for_node(node_id=1)
    assert assignment is not None
```

- [ ] **Step 2: Run the targeted repo/service tests to verify they fail**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/unit/modules/taxonomy/test_repo.py tests/unit/modules/taxonomy/test_service.py -v
```

Expected: FAIL because repo/service boundaries do not exist.

- [ ] **Step 3: Implement the minimal taxonomy module boundaries**

Implement:
- repository methods for:
  - tree read
  - child read ordered by `name ASC`
  - final assignment lookup by `node_id`
  - final assignment write/update path
- service methods that expose only accepted tree/assignment operations
- import-linter rule if needed so downstream modules consume taxonomy through ports/service boundaries rather than direct repo/model imports

Avoid:
- HTTP endpoint introduction
- workflow-state or candidate APIs
- duplicated tree traversal logic across repo and service
- silent "best effort" assignment overwrite behavior

- [ ] **Step 4: Run targeted tests and architecture checks**

Run:

```bash
cd /Users/mianqin/Code/knowledge/apps/api
.venv/bin/python -m pytest tests/unit/modules/taxonomy/test_repo.py tests/unit/modules/taxonomy/test_service.py -v
uvx ruff check src/modules/taxonomy tests/unit/modules/taxonomy
ty check src/modules/taxonomy tests/unit/modules/taxonomy
```

Expected: PASS

- [ ] **Step 5: Controller finalizes task**

Confirm:
- Tree reads and assignment reads/writes are available through one clear module boundary
- Sibling ordering is consistently `name ASC`
- No HTTP transport or LLM workflow logic was added
- Related spec files remain current and synchronized with the implemented taxonomy module boundaries

---

## Plan Coverage Gate

| Design commitment | Task IDs | Files | Tests / Checks | Spec synchronization evidence |
| --- | --- | --- | --- | --- |
| Taxonomy is a dedicated backend module | `T01`, `T04` | `apps/api/src/modules/taxonomy/*` | unit tests for model/repo/service; static checks | `taxonomy.md`, `01-system-modules.md`, `04-repository-structure.md` remain current |
| Taxonomy tree persists in dedicated tables without changing `knowledge_graph` tables | `T01` | `model.py`, table migration, `alembic/env.py` | model-projection test, autogenerate verification | `08-persistence-schema-projection.md` remains current |
| Each knowledge node binds to exactly one final taxonomy leaf | `T01`, `T02`, `T04` | assignment model, trigger migration, repo/service write path | trigger integration test, repo/service tests | `taxonomy.md`, `08-persistence-schema-projection.md`, `10-migration-lifecycle-governance.md` remain current |
| Leaf-only enforcement is database truth via a dedicated hand-authored trigger migration | `T02` | dedicated trigger revision | integration trigger test | `taxonomy.md`, `10-migration-lifecycle-governance.md` remain current |
| Taxonomy import is bootstrap-only and fails on non-empty storage | `T03` | `importer.py`, import script | importer unit test, import integration test | `taxonomy.md`, `knowledge-ingestion-search-orchestration.md` remain current |
| Semantic-map will consume taxonomy as high-level structure truth later, but this slice does not implement that consumer change | `T04` | taxonomy ports/service only | architecture/static checks | `semantic-map.md` remains current; no semantic-map runtime change is introduced in this plan |

Coverage review:
- No task depends on workaround-only behavior; root-cause fixes are used for import guard, trigger enforcement, and ordering.
- No task uses silent failure or hidden fallback; import/store checks fail explicitly.
- No task introduces over-defensive workflow-state persistence beyond the accepted scope.
- Each task ends with one controller-owned finalization step that includes verification and spec synchronization confirmation.

Plan complete and saved to `/Users/mianqin/Code/knowledge/.orbital/specs/plans/2026-04-04-taxonomy-module-foundation-plan.md`. Ready to execute?
