---
abstract: Implementation plan for the project-owned source-pipeline orchestrator that drives `page-to-card` and `card-review` through `job-queue-mcp` with minimal local persistence.
out_of_scope: Source discovery, source-side processed bookkeeping, `job-queue-mcp` worker implementation, and final reviewed-card persistence.
---

# Source Pipeline Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-04-20-source-pipeline-orchestrator-plan`

**Goal:** Build a project-owned `apps/source_pipeline` app that accepts external source-processing requests, submits `page-to-card` jobs to `job-queue-mcp`, fans accepted cards out into `card-review` jobs, and hands accepted review results downstream while persisting only the minimum local linkage state.

**Architecture:** The implementation adds one independent Python app, `apps/source_pipeline`, plus one long-running `orchestrator` process. The app keeps source logic outside the repository boundary, stores only `workflow_runs`, `workflow_units`, and `card_review_jobs`, reads accepted results back from `job-queue-mcp` instead of mirroring queue state locally, and exports JSON Schema directly from Python contracts for both step types.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/01-system-modules.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/03-architecture-constraints.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus.md`

**Assumptions and Constraints:**
- External source services handle source reading and source-side processed bookkeeping before calling this app.
- `job-queue-mcp` accepted results are rereadable and non-consuming through `GET /results/{job_id}`.
- This app does not persist accepted `cards[]`, review payloads, queue lifecycle mirrors, leases, or submission history.
- Primary keys use auto-incrementing integer columns only.
- JSON Schema is exported directly from Python contracts; no hand-written duplicate schema files are introduced.
- Root-cause fixes are required; do not add fallback state, silent retries, or defensive shadow persistence that duplicates queue truth.

**Decision Gates:** None.

**Tech Stack:** Python 3.14, SQLAlchemy asyncio, Alembic, Pydantic v2, `pydantic-settings`, `httpx`, Docker Compose, pytest, pytest-anyio, Ruff, Ty.

---

## Planned File Structure

- `/Users/mianqin/Code/knowledge/pyproject.toml`
  Add the new workspace member.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/pyproject.toml`
  Define the new app package and its dependencies.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/alembic.ini`
  Migration entrypoint for source-pipeline tables.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/alembic/env.py`
  Alembic runtime bootstrap for the app-local metadata.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/alembic/versions/*.py`
  Initial migration for `workflow_runs`, `workflow_units`, and `card_review_jobs`.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/config.py`
  Pydantic settings for DB URL, queue base URL, tokens, and poll interval.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/db/base.py`
  SQLAlchemy base and naming convention.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/db/session.py`
  Async engine/session factory.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/db/models.py`
  Minimal local persistence models.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_intake/service.py`
  Intake materialization for `workflow_runs` and `workflow_units`.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_runtime/job_queue_client.py`
  Thin HTTP client over `POST /producer/jobs` and `GET /results/{job_id}`.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_runtime/service.py`
  The orchestrator tick loop and transition logic.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/page_to_card/contracts.py`
  `SourceUnit`, `CardDraft`, and exported `page-to-card` output schema.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/card_review/contracts.py`
  `ReviewItem`, `ReviewResult`, and exported `card-review` output schema.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_handoff/ports.py`
  Narrow downstream handoff protocol.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/entrypoints/orchestrator.py`
  Long-running process bootstrap and tick scheduling.
- `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/**`
  Unit and integration tests for contracts, persistence, queue client, and runtime flow.
- `/Users/mianqin/Code/knowledge/infra/docker/source_pipeline/Dockerfile`
  Build/runtime image for the orchestrator role.
- `/Users/mianqin/Code/knowledge/infra/docker/source_pipeline/run-orchestrator.sh`
  Stable startup wrapper for the long-running process.
- `/Users/mianqin/Code/knowledge/infra/compose/docker-compose.base.yml`
  Dedicated `orchestrator` service definition.

## Chunk 1: App Foundation and Minimal Persistence

### Task T01: Create the `apps/source_pipeline` App and Its Minimal Persistence Model

**Task ID:** `T01`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create:
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/pyproject.toml`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/alembic.ini`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/alembic/env.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/alembic/versions/2026_04_20_000001_initial_source_pipeline.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/config.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/db/base.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/db/session.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/db/models.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_models.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_config.py`
- Modify:
  - `/Users/mianqin/Code/knowledge/pyproject.toml`
  - `/Users/mianqin/Code/knowledge/uv.lock`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`

- [ ] **Step 1: Write the failing tests for settings and the three-table model projection**

```python
def test_source_pipeline_settings_require_explicit_urls() -> None:
    with pytest.raises(ValidationError):
        SourcePipelineSettings()


def test_workflow_unit_projection_stores_only_minimal_linkage_state() -> None:
    columns = WorkflowUnit.__table__.c.keys()
    assert columns == [
        "id",
        "workflow_run_id",
        "source_kind",
        "source_ref",
        "payload",
        "page_to_card_job_id",
        "created_at",
    ]


def test_card_review_job_projection_uses_integer_pk_and_handoff_flag() -> None:
    columns = CardReviewJob.__table__.c.keys()
    assert columns == [
        "id",
        "workflow_unit_id",
        "ordinal",
        "job_queue_job_id",
        "handoff_done",
        "created_at",
    ]
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_models.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_config.py -v`

Expected:
- FAIL because the app package, models, and settings do not exist yet

- [ ] **Step 3: Implement the app skeleton, settings, models, and initial migration**

Implement:
- Add `apps/source_pipeline` to the root workspace.
- Create a standalone app package that mirrors the repository’s existing app pattern.
- Add `SourcePipelineSettings` with explicit fields for:
  - database URL
  - job-queue base URL
  - producer token
  - results-reader token
  - poll interval / batch size settings
- Create SQLAlchemy models with auto-incrementing integer primary keys only:
  - `WorkflowRun`
  - `WorkflowUnit`
  - `CardReviewJob`
- Keep the model surface minimal:
  - no mirrored queue state
  - no accepted payload columns
  - no processed-bookkeeping fields
- Add one initial Alembic migration that creates exactly those three tables.

- [ ] **Step 4: Run the targeted tests and migration checks**

Run:
- `uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_models.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_config.py -v`
- `uv run --package source-pipeline alembic -c /Users/mianqin/Code/knowledge/apps/source_pipeline/alembic.ini upgrade head`

Expected:
- PASS for the unit tests
- Alembic upgrade completes without schema errors

- [ ] **Step 5: Controller finalizes task**

Confirm:
- `apps/source_pipeline` exists as a workspace member with its own app-local runtime/config/migration assets
- Only `workflow_runs`, `workflow_units`, and `card_review_jobs` are introduced locally
- Targeted tests and migration checks pass with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No generalized `step_jobs` mirror of queue state
- No defensive “future-proof” columns without an approved need
- No reuse of `apps/api` config loaders or entrypoint code

## Chunk 2: Step Contracts and Queue Client

### Task T02: Define `page-to-card` and `card-review` Contracts and Add the Thin Queue Client

**Task ID:** `T02`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create:
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/page_to_card/contracts.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/card_review/contracts.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_runtime/job_queue_client.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_page_to_card_contracts.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_card_review_contracts.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_job_queue_client.py`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`

- [ ] **Step 1: Write the failing tests for contract shape and queue projection**

```python
def test_page_to_card_schema_is_exported_from_python_contracts() -> None:
    schema = export_page_to_card_output_schema()
    assert schema["type"] == "array"
    assert schema["items"]["required"] == ["title", "content"]


def test_card_review_schema_is_exported_from_python_contracts() -> None:
    schema = export_card_review_output_schema()
    assert schema["type"] == "object"
    assert "title_validity" in schema["properties"]
    assert "passed" not in schema["properties"]


async def test_get_result_returns_not_ready_and_terminal_state() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            202,
            json={"job_id": 7, "state": "FAILED", "result_ready": False},
        )
    )
    client = JobQueueClient(base_url="http://queue", results_token="token", transport=transport)

    result = await client.get_result(job_id=7)

    assert result.kind == "not_ready"
    assert result.state == "FAILED"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_page_to_card_contracts.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_card_review_contracts.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_job_queue_client.py -v`

Expected:
- FAIL because the contract modules and queue client do not exist yet

- [ ] **Step 3: Implement the step contracts and the thin queue client**

Implement:
- `SourceUnit` with:
  - `source_kind`
  - `source_ref`
  - `title`
  - `content`
  - `metadata`
- `CardDraft` with exactly:
  - `title`
  - `content`
- `ReviewItem` and `ReviewResult` using the existing six review dimensions only
- One export function per step:
  - `export_page_to_card_output_schema()`
  - `export_card_review_output_schema()`
- One queue client with only the methods the orchestrator needs:
  - `create_job(...)`
  - `get_result(job_id: int)`
- Keep the queue client narrow:
  - use `POST /producer/jobs`
  - use `GET /results/{job_id}`
  - treat `200` as accepted result
  - treat `202` as not-ready plus current queue state
  - do not add operator-history wrappers or lease APIs

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:
`uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_page_to_card_contracts.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_card_review_contracts.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_job_queue_client.py -v`

Expected:
- PASS for schema export and queue projection behavior

- [ ] **Step 5: Controller finalizes task**

Confirm:
- Both step schemas are exported directly from Python contracts
- The queue client uses only the producer and results surfaces
- No hand-written duplicate schema artifacts were introduced
- Targeted tests pass with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No local JSON Schema copies checked into the repo
- No broad queue client that wraps surfaces the orchestrator does not need
- No fake aggregate `passed` field added on top of `ReviewResult`

## Chunk 3: Intake, Runtime, and Handoff Flow

### Task T03: Implement Intake Materialization and the Orchestrator Tick Loop

**Task ID:** `T03`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create:
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_intake/service.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_runtime/service.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/pipeline_handoff/ports.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_pipeline_intake_service.py`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_pipeline_runtime_service.py`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/01-system-modules.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`

- [ ] **Step 1: Write the failing tests for materialization, fan-out, reread, and handoff**

```python
async def test_materialize_config_creates_run_and_units(db_session: AsyncSession) -> None:
    service = PipelineIntakeService(db_session)

    run = await service.create_run(
        source_kind="external",
        config_payload={"units": [{"source_ref": "a", "title": "A", "content": "x"}]},
    )

    assert run.id == 1
    units = await list_units_for_run(db_session, run.id)
    assert len(units) == 1
    assert units[0].page_to_card_job_id is None


async def test_tick_submits_page_to_card_when_job_id_missing(...) -> None:
    ...
    assert unit.page_to_card_job_id == 12


async def test_tick_rereads_page_to_card_result_and_fans_out_reviews(...) -> None:
    ...
    assert [job.ordinal for job in review_jobs] == [0, 1]
    assert [job.job_queue_job_id for job in review_jobs] == [21, 22]


async def test_tick_marks_handoff_done_without_persisting_review_payload(...) -> None:
    ...
    assert review_job.handoff_done is True
    assert "result_payload" not in CardReviewJob.__table__.c.keys()
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_pipeline_intake_service.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_pipeline_runtime_service.py -v`

Expected:
- FAIL because the services and runtime tick logic do not exist yet

- [ ] **Step 3: Implement the minimal intake and runtime flow**

Implement:
- `PipelineIntakeService.create_run(...)` that:
  - inserts one `workflow_runs` row
  - normalizes input units into `SourceUnit` payload snapshots
  - inserts one `workflow_units` row per unit
- `PipelineRuntimeService.tick(...)` that:
  - submits `page-to-card` for units with `page_to_card_job_id is null`
  - rereads page results from the queue
  - creates missing `card_review_jobs` by ordinal
  - submits review jobs for rows with `job_queue_job_id is null`
  - rereads review results from the queue
  - calls the downstream handoff port
  - sets only `handoff_done=true` after successful handoff
- Keep runtime decisions explicit:
  - `202 + state in ("PENDING", "LEASED", "FAILED")` means no accepted result yet
  - `202 + state == "DEAD_LETTER"` is terminal failure
  - `200` means reread the accepted payload and advance
- Do not persist:
  - `cards[]`
  - review payloads
  - queue lifecycle mirrors
  - poll counters / lease metadata unless a concrete failure proves they are required

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:
`uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_pipeline_intake_service.py /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_pipeline_runtime_service.py -v`

Expected:
- PASS for materialization, queue reread, fan-out, and handoff behavior

- [ ] **Step 5: Controller finalizes task**

Confirm:
- Intake creates only the minimum local rows needed by the orchestrator
- The runtime rereads queue results instead of mirroring them locally
- Review handoff completion is the only persisted per-review terminal marker
- Targeted tests pass with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No shadow queue state machine inside this repository
- No stored accepted payloads “for safety”
- No silent handoff failure swallowing; handoff errors must fail explicitly

## Chunk 4: Process Entrypoint and Compose Integration

### Task T04: Add the Long-Running `orchestrator` Role

**Task ID:** `T04`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create:
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/src/source_pipeline/entrypoints/orchestrator.py`
  - `/Users/mianqin/Code/knowledge/infra/docker/source_pipeline/Dockerfile`
  - `/Users/mianqin/Code/knowledge/infra/docker/source_pipeline/run-orchestrator.sh`
  - `/Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_orchestrator_entrypoint.py`
- Modify:
  - `/Users/mianqin/Code/knowledge/infra/compose/docker-compose.base.yml`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`

- [ ] **Step 1: Write the failing tests for process bootstrap and compose registration**

```python
def test_orchestrator_entrypoint_builds_runtime_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(module, "run_forever", lambda runtime: calls.append("run"))

    module.main()

    assert calls == ["run"]


def test_compose_contains_orchestrator_service() -> None:
    compose = Path("/Users/mianqin/Code/knowledge/infra/compose/docker-compose.base.yml").read_text()
    assert "orchestrator:" in compose
    assert "run-orchestrator.sh" in compose
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_orchestrator_entrypoint.py -v`

Expected:
- FAIL because the entrypoint and service wiring do not exist yet

- [ ] **Step 3: Implement the entrypoint, image, and compose role**

Implement:
- An app-local orchestrator bootstrap that:
  - loads settings
  - constructs DB session factory
  - constructs queue client and handoff implementation
  - loops forever with one explicit sleep interval between ticks
- A dedicated Docker image under `infra/docker/source_pipeline`
- A dedicated shell wrapper `run-orchestrator.sh`
- One `orchestrator` service in `docker-compose.base.yml`
  - depends on the existing `postgres` and its migration gate
  - exposes no public port
  - uses explicit env vars for DB URL and queue credentials

- [ ] **Step 4: Run the targeted tests and configuration checks**

Run:
- `uv run --package source-pipeline pytest /Users/mianqin/Code/knowledge/apps/source_pipeline/tests/unit/test_orchestrator_entrypoint.py -v`
- `docker compose -f /Users/mianqin/Code/knowledge/infra/compose/docker-compose.base.yml config >/tmp/source-pipeline-compose.txt`

Expected:
- PASS for the entrypoint test
- `docker compose config` renders successfully with the new `orchestrator` role

- [ ] **Step 5: Controller finalizes task**

Confirm:
- The repository has a dedicated long-running `orchestrator` role
- The role is separate from the existing ingestion `worker`
- Compose wiring and startup paths are valid
- Targeted tests/checks pass with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No reuse of the Dramatiq worker role for unrelated orchestration work
- No extra public HTTP surface introduced for this runtime by default
- No hidden startup fallback behavior when required env vars are missing

## Plan Coverage Gate

| Design commitment | Task IDs | Files | Tests / Checks | Spec synchronization evidence |
| --- | --- | --- | --- | --- |
| Source pipeline is a project-owned app under `apps/source_pipeline` | `T01`, `T04` | `pyproject.toml`, `apps/source_pipeline/**`, `infra/docker/source_pipeline/**`, `infra/compose/docker-compose.base.yml` | `pytest ...test_models.py ...test_config.py`, `pytest ...test_orchestrator_entrypoint.py`, `docker compose ... config` | `T01` and `T04` finalization confirm `04-repository-structure.md` and `knowledge-corpus-page-card-orchestration.md` stay current |
| Local persistence is limited to `workflow_runs`, `workflow_units`, and `card_review_jobs` | `T01`, `T03` | `apps/source_pipeline/src/source_pipeline/db/models.py`, Alembic migration, runtime service | `pytest ...test_models.py`, `pytest ...test_pipeline_runtime_service.py` | `T01` and `T03` finalization confirm `knowledge-corpus-page-card-orchestration.md` remains synchronized |
| `page-to-card` returns bare `cards[]` and `card-review` keeps the six review dimensions | `T02` | `page_to_card/contracts.py`, `card_review/contracts.py` | `pytest ...test_page_to_card_contracts.py ...test_card_review_contracts.py` | `T02` finalization confirms the step contracts remain synchronized with the design doc |
| The orchestrator rereads queue truth instead of mirroring queue state locally | `T02`, `T03` | `pipeline_runtime/job_queue_client.py`, `pipeline_runtime/service.py` | `pytest ...test_job_queue_client.py`, `pytest ...test_pipeline_runtime_service.py` | `T02` and `T03` finalization confirm the design still states queue-as-truth |
| Each returned card fans out into one review job and accepted review results are handed off immediately | `T03` | `pipeline_runtime/service.py`, `pipeline_handoff/ports.py` | `pytest ...test_pipeline_runtime_service.py` | `T03` finalization confirms `knowledge-corpus-page-card-orchestration.md` and `01-system-modules.md` stay current |
| The runtime is separate from the ingestion worker and runs as a dedicated compose role | `T04` | `entrypoints/orchestrator.py`, `infra/docker/source_pipeline/**`, `infra/compose/docker-compose.base.yml` | `pytest ...test_orchestrator_entrypoint.py`, `docker compose ... config` | `T04` finalization confirms `04-repository-structure.md` and `01-system-modules.md` stay current |

Plan complete and saved to `/Users/mianqin/Code/knowledge/.orbital/specs/plans/2026-04-20-source-pipeline-orchestrator-plan.md`. Ready to execute?
