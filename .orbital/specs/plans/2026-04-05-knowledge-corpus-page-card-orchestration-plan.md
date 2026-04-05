---
abstract: Implementation plan for an external page-to-card orchestration library that runs one Cursor session per page and routes card writes through the existing reviewed card CLI.
out_of_scope: Topic filtering, page discovery, card deduplication, downstream ingestion durability confirmation, and changes to knowledge corpus schema ownership.
---

# Knowledge Corpus Page-Card Orchestration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Plan ID:** `2026-04-05-knowledge-corpus-page-card-orchestration-plan`

**Goal:** Build an external `human_workspace` orchestration library that accepts complete page records, runs one Cursor page session per page with bounded concurrency, writes cards through the existing `apps/cli` command surface, and marks `knowledge_corpus` pages processed only after page-level `handoff_complete`.

**Architecture:** The implementation keeps page-to-card orchestration outside app ownership boundaries. `apps/cli` gains one shared reviewed-submission Python function so the CLI wrapper and any future import-based callers stay behaviorally aligned, while the page agent itself uses the existing write-card CLI command inside a page-scoped Cursor session. `human_workspace` owns page contracts, Cursor session execution, and the thread-pooled `run_pages(...)` orchestrator that calls `knowledge_corpus.wikipedia.service.mark_document_processed(...)` only for completed pages.

**Input Specs:**
- Requirements: `/Users/mianqin/Code/knowledge/.orbital/specs/requirements.md`
- Designs:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/cli.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/cli-review-orchestration.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`

**Assumptions and Constraints:**
- The first version does not discover or filter pages; callers supply complete page records.
- The first version does not implement deduplication or replay protection for cards.
- A failed page ends as `failed`; the orchestrator does not automatically rerun failed pages.
- `processed` means `handoff_complete`, not durable downstream persistence.
- The page agent uses the existing reviewed card CLI command inside the Cursor session; the orchestrator itself remains library-first.
- `human_workspace` remains a flat script/module area, so new modules should follow the existing `wiki_*` naming style instead of introducing a new package layout.
- Root-cause fixes are required; do not add wrapper behavior that hides malformed Cursor output, rejected cards, or processed-mark failures.

**Decision Gates:** None.

**Tech Stack:** Python 3.14, Click, Cursor Agent headless CLI, subprocess, `concurrent.futures`, async SQLAlchemy through `knowledge_corpus`, pytest, pytest-anyio, Ruff.

---

## Chunk 1: Shared Reviewed-Submission Boundary in `apps/cli`

### Task T01: Expose a Shared Reviewed-Submission Python Function Behind the Existing CLI

**Task ID:** `T01`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify:
  - `/Users/mianqin/Code/knowledge/apps/cli/main.py`
  - `/Users/mianqin/Code/knowledge/apps/cli/tests/test_main.py`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/cli.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/cli-review-orchestration.md`

- [ ] **Step 1: Write the failing tests for the shared reviewed-submission function and CLI projection**

```python
def test_submit_reviewed_card_returns_review_result_when_review_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = ReviewResult(
        title_validity=ReviewItem(passed=True, reason=None),
        title_content_alignment=ReviewItem(passed=True, reason=None),
        content_coherence=ReviewItem(passed=True, reason=None),
        content_atomicity=ReviewItem(passed=True, reason=None),
        content_latex_validity=ReviewItem(passed=True, reason=None),
    )

    monkeypatch.setattr(main, "run_review_graph", lambda payload, settings: expected)

    review = main.submit_reviewed_card(
        title="Quadratic Equation Standard Form",
        content="A quadratic equation has the form \\(ax^2 + bx + c = 0\\).",
    )

    assert review == expected


def test_cli_projects_shared_function_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_review = ReviewResult(
        title_validity=ReviewItem(passed=False, reason="too broad"),
        title_content_alignment=ReviewItem(passed=True, reason=None),
        content_coherence=ReviewItem(passed=True, reason=None),
        content_atomicity=ReviewItem(passed=True, reason=None),
        content_latex_validity=ReviewItem(passed=True, reason=None),
    )
    monkeypatch.setattr(main, "submit_reviewed_card", lambda title, content: failed_review)

    runner = CliRunner()
    result = runner.invoke(
        main.cli,
        ["--title", "Math", "--content", "A quadratic equation has the form \\(ax^2 + bx + c = 0\\)."],
    )

    assert result.exit_code == 1
    assert json.loads(result.output)["result"] == "failed"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`uv run --package cli pytest /Users/mianqin/Code/knowledge/apps/cli/tests/test_main.py -v`

Expected:
- FAIL because `submit_reviewed_card(...)` does not exist yet and the CLI still owns the full flow directly

- [ ] **Step 3: Implement the shared reviewed-submission boundary**

Implement:
- A new importable function in `/Users/mianqin/Code/knowledge/apps/cli/main.py`:
  - `submit_reviewed_card(title: str, content: str, settings: CliSettings | None = None) -> ReviewResult`
- The function must:
  - validate `title` and `content` through the existing `CardInput`
  - build default `CliSettings` only when no settings instance is supplied
  - execute the existing graph path exactly once
  - return the `ReviewResult`
  - raise on local runtime failure instead of serializing terminal output
- Refactor the Click command so it becomes a thin wrapper:
  - parse arguments
  - call `submit_reviewed_card(...)`
  - serialize terminal JSON through the existing `serialize_review_result(...)`
  - preserve the existing `0/1` exit-code contract

Keep this task focused:
- do not change the current review dimensions
- do not change the current CLI stdout contract
- do not move code into multiple new CLI files yet

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:
`uv run --package cli pytest /Users/mianqin/Code/knowledge/apps/cli/tests/test_main.py -v`

Expected:
- PASS for the shared entrypoint and CLI projection tests

- [ ] **Step 5: Controller finalizes task**

Confirm:
- `apps/cli` exposes one importable reviewed-submission function and the Click command is only a thin wrapper over it
- The shared function and CLI wrapper project the same review/submission behavior
- Targeted tests are passing with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No duplicated review/submission logic across library and CLI entrypoints
- No wrapper that swallows runtime failures into fake success payloads
- No new ad hoc result contract divorced from the existing `ReviewResult`

## Chunk 2: Page Contracts and One-Page Cursor Session Runner

### Task T02: Add Page Record/Result Contracts and a Page-Scoped Cursor Runner

**Task ID:** `T02`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create:
  - `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_types.py`
  - `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_cursor.py`
  - `/Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_cursor.py`
- Modify:
  - `/Users/mianqin/Code/knowledge/human_workspace/pyproject.toml`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/04-repository-structure.md`

- [ ] **Step 1: Write the failing tests for page contracts, prompt construction, and page-result parsing**

```python
def test_build_page_agent_prompt_includes_page_fields_and_cli_command() -> None:
    page = PageRecord(
        page_id=42,
        url="https://en.wikipedia.org/wiki/Quadratic_equation",
        title="Quadratic equation",
        clean_text="A quadratic equation is a polynomial equation of degree two.",
    )

    prompt = build_page_agent_prompt(
        page,
        write_card_command=[
            "uv",
            "run",
            "--package",
            "cli",
            "python",
            "/Users/mianqin/Code/knowledge/apps/cli/main.py",
        ],
    )

    assert "Quadratic equation" in prompt
    assert "A quadratic equation is a polynomial equation of degree two." in prompt
    assert "--title" in prompt
    assert "--content" in prompt
    assert '"status"' in prompt


def test_run_page_session_returns_page_result_from_cursor_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = PageRecord(
        page_id=42,
        url="https://en.wikipedia.org/wiki/Quadratic_equation",
        title="Quadratic equation",
        clean_text="A quadratic equation is a polynomial equation of degree two.",
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"type":"result","result":"{\\"page_id\\":42,\\"status\\":\\"completed\\"}"}',
            stderr="",
        ),
    )

    result = run_page_session(page, settings=PageAgentSettings())

    assert result.page_id == 42
    assert result.status == "completed"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`uv --project /Users/mianqin/Code/knowledge/human_workspace run pytest /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_cursor.py -v`

Expected:
- FAIL because the page-card modules and contracts do not exist yet

- [ ] **Step 3: Implement the page contracts and one-page Cursor runner**

Implement:
- `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_types.py`
  - `PageRecord`
  - `PageResult`
  - `PageResult.status` limited to `completed | failed`
- `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_cursor.py`
  - a settings/config object for Cursor command, workspace root, timeout, and write-card command base
  - `build_write_card_command(...)` that resolves the existing CLI invocation:
    - `uv run --package cli python /Users/mianqin/Code/knowledge/apps/cli/main.py --title ... --content ...`
  - `build_page_agent_prompt(...)` that:
    - injects the page data
    - tells Cursor to keep extracting cards until no more worthwhile atomic cards remain
    - tells Cursor to use the existing write-card CLI command for each card
    - requires the final answer to be JSON matching the `PageResult` schema and nothing else
  - `run_page_session(...)` that:
    - starts one headless Cursor session per page
    - invokes `cursor-agent` in agentic headless mode with `--print --output-format json --sandbox enabled --trust --workspace <isolated-page-workspace>` so the session can use the write-card CLI command while remaining scoped to an isolated workspace
    - uses an isolated workspace directory under a caller-configurable root
    - parses Cursor's outer JSON payload
    - validates the final page result into `PageResult`
    - raises on malformed output or command failure
- `/Users/mianqin/Code/knowledge/human_workspace/pyproject.toml`
  - add the new `wiki_page_to_cards_*` modules to the setuptools `py-modules` list

Implementation constraints for this task:
- the page session must use the existing write-card CLI command, not a new MCP tool
- the first version must not add page replay logic
- the Cursor runner must not swallow malformed output; malformed final output is a failure

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:
`uv --project /Users/mianqin/Code/knowledge/human_workspace run pytest /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_cursor.py -v`

Expected:
- PASS for page contract and page-runner tests

- [ ] **Step 5: Controller finalizes task**

Confirm:
- The new page-card modules exist under `human_workspace` using the repository's current flat `wiki_*` naming style
- One page maps to one Cursor session and one final `PageResult`
- The page prompt points Cursor at the existing write-card CLI command rather than a new tool surface
- Targeted tests are passing with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No new card-write protocol layered on top of the existing CLI contract
- No fake fallback result when Cursor returns malformed JSON
- No early package refactor of `human_workspace`; keep file placement aligned with current repository reality

## Chunk 3: Thread-Pooled Orchestration and Processed Marking

### Task T03: Implement `run_pages(...)` with Bounded Concurrency and `handoff_complete` Processed Marks

**Task ID:** `T03`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Create:
  - `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_orchestrator.py`
  - `/Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_orchestrator.py`
- Modify:
  - `/Users/mianqin/Code/knowledge/human_workspace/pyproject.toml`
  - `/Users/mianqin/Code/knowledge/human_workspace/tests/conftest.py`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus.md`

- [ ] **Step 1: Write the failing tests for processed marking, failure isolation, and bounded worker execution**

```python
def test_run_pages_marks_only_completed_pages() -> None:
    pages = [
        PageRecord(page_id=1, url="u1", title="t1", clean_text="c1"),
        PageRecord(page_id=2, url="u2", title="t2", clean_text="c2"),
    ]
    seen_marks: list[tuple[int, str]] = []

    def fake_runner(page: PageRecord) -> PageResult:
        return PageResult(page_id=page.page_id, status="completed" if page.page_id == 1 else "failed")

    def fake_mark_processed(*, page_id: int, external_target_ref: str) -> None:
        seen_marks.append((page_id, external_target_ref))

    results = run_pages(
        pages,
        max_workers=2,
        run_page_session=fake_runner,
        mark_processed=fake_mark_processed,
    )

    assert [result.status for result in results] == ["completed", "failed"]
    assert seen_marks == [(1, "cursor-page-agent:wikipedia:1")]


def test_run_pages_keeps_other_pages_running_when_one_fails() -> None:
    pages = [
        PageRecord(page_id=1, url="u1", title="t1", clean_text="c1"),
        PageRecord(page_id=2, url="u2", title="t2", clean_text="c2"),
    ]

    def fake_runner(page: PageRecord) -> PageResult:
        if page.page_id == 1:
            raise RuntimeError("cursor failed")
        return PageResult(page_id=2, status="completed")

    results = run_pages(
        pages,
        max_workers=2,
        run_page_session=fake_runner,
        mark_processed=lambda **kwargs: None,
    )

    assert {result.page_id: result.status for result in results} == {1: "failed", 2: "completed"}
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:
`uv --project /Users/mianqin/Code/knowledge/human_workspace run pytest /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_orchestrator.py -v`

Expected:
- FAIL because the orchestrator module and `run_pages(...)` do not exist yet

- [ ] **Step 3: Implement the top-level orchestration library**

Implement:
- `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_orchestrator.py`
  - `run_pages(pages, *, max_workers, run_page_session=..., mark_processed=...) -> list[PageResult]`
  - a bounded `ThreadPoolExecutor`
  - one worker action per page
  - deterministic `external_target_ref` generation in the exact form `cursor-page-agent:wikipedia:<page_id>`
  - processed marking only after `PageResult(status="completed")`
  - failure isolation so one page failure does not stop the remaining futures
  - no automatic replay and no card-level checkpointing
  - a thin processed-mark adapter that:
    - loads `knowledge_corpus` settings through `knowledge_corpus.config.load_settings()`
    - builds one async engine and session factory through `knowledge_corpus.db.session.build_session_factory(...)`
    - opens an async session boundary and calls `knowledge_corpus.wikipedia.service.mark_document_processed(...)`
    - runs only after a page reaches `completed`
    - disposes the engine when `run_pages(...)` finishes
- `/Users/mianqin/Code/knowledge/human_workspace/tests/conftest.py`
  - any shared fixtures needed for page records or orchestrator dependency injection
- `/Users/mianqin/Code/knowledge/human_workspace/pyproject.toml`
  - add the new orchestrator module to `py-modules`

Implementation constraints for this task:
- do not move processed marking into `apps/knowledge_corpus`
- do not write directly to SQL from `human_workspace`; use the existing `knowledge_corpus.wikipedia.service.mark_document_processed(...)` boundary
- do not add page replay, backoff, or checkpoint state
- if processed marking raises, the page result must be `failed` for that workflow attempt

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:
`uv --project /Users/mianqin/Code/knowledge/human_workspace run pytest /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_orchestrator.py -v`

Expected:
- PASS for processed-marking and failure-isolation tests

- [ ] **Step 5: Controller finalizes task**

Confirm:
- `run_pages(...)` exists as the primary library entrypoint
- processed marking happens only for completed pages and uses the accepted deterministic reference string
- page failures are isolated and are not automatically replayed
- Targeted tests are passing with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No hidden retry loop that contradicts the accepted first-version semantics
- No direct SQL or duplicate repository logic in `human_workspace`
- No “partial success” state written into `processed_documents`

## Chunk 4: End-to-End Workflow Verification and Plan Handoff

### Task T04: Add End-to-End Library Tests for One-Page Completion and Shared-Boundary Reuse

**Task ID:** `T04`
**Task Finalization Ownership:** Controller at task end (single finalization step)

**Files:**
- Modify:
  - `/Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_cursor.py`
  - `/Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_orchestrator.py`
  - `/Users/mianqin/Code/knowledge/apps/cli/tests/test_main.py`
- Spec:
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/knowledge-corpus-page-card-orchestration.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/cli.md`
  - `/Users/mianqin/Code/knowledge/.orbital/specs/designs/cli-review-orchestration.md`

- [ ] **Step 1: Write the failing tests for the complete handoff path**

```python
def test_run_pages_completed_flow_uses_existing_write_card_command_and_marks_processed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = PageRecord(
        page_id=42,
        url="https://en.wikipedia.org/wiki/Quadratic_equation",
        title="Quadratic equation",
        clean_text="A quadratic equation is a polynomial equation of degree two.",
    )
    captured_commands: list[str] = []
    captured_marks: list[tuple[int, str]] = []

    monkeypatch.setattr(
        wiki_page_to_cards_cursor,
        "build_page_agent_prompt",
        lambda page, write_card_command: (
            captured_commands.append(" ".join(write_card_command))
            or '{"page_id":42,"status":"completed"}'
        ),
    )

    # additional monkeypatches here should simulate the Cursor outer payload and processed mark call

    results = run_pages(
        [page],
        max_workers=1,
        run_page_session=fake_completed_session,
        mark_processed=fake_mark_processed,
    )

    assert results == [PageResult(page_id=42, status="completed")]
    assert captured_marks == [(42, "cursor-page-agent:wikipedia:42")]
```

- [ ] **Step 2: Run the combined targeted tests to verify they fail**

Run:
`uv run --package cli pytest /Users/mianqin/Code/knowledge/apps/cli/tests/test_main.py -v && uv --project /Users/mianqin/Code/knowledge/human_workspace run pytest /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_cursor.py /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_orchestrator.py -v`

Expected:
- FAIL because the end-to-end boundary assertions are not covered yet

- [ ] **Step 3: Implement the minimal end-to-end assertions**

Implement:
- shared test helpers that prove:
  - the page runner points Cursor at the existing write-card CLI command
  - the CLI wrapper still projects the shared reviewed-submission function
  - a completed page produces the processed mark and a failed page does not
- only the minimal helper extraction necessary to avoid duplicated setup across the new tests

- [ ] **Step 4: Run the combined targeted tests to verify they pass**

Run:
`uv run --package cli pytest /Users/mianqin/Code/knowledge/apps/cli/tests/test_main.py -v && uv --project /Users/mianqin/Code/knowledge/human_workspace run pytest /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_cursor.py /Users/mianqin/Code/knowledge/human_workspace/tests/test_wiki_page_to_cards_orchestrator.py -v`

Expected:
- PASS for the combined shared-boundary and orchestration tests

- [ ] **Step 5: Controller finalizes task**

Confirm:
- The page-card workflow is covered from page input through Cursor session result and processed marking
- The existing write-card CLI command remains the page-agent tool surface
- The CLI wrapper still remains a thin projection over the shared Python function
- Targeted tests are passing with expected outcomes
- Related spec files remain current and synchronized

**Anti-Pattern Avoidance Notes:**
- No fake “green” integration test that skips the actual command shape being handed to Cursor
- No second write-card implementation path outside `apps/cli`
- No extra result metadata beyond the accepted page/result contracts

## Plan Coverage Gate

| Design commitment | Task IDs | File paths | Tests | Spec synchronization |
| --- | --- | --- | --- | --- |
| `apps/cli` exposes one shared reviewed-submission Python entrypoint and keeps the CLI as a thin wrapper | `T01`, `T04` | `/Users/mianqin/Code/knowledge/apps/cli/main.py`, `/Users/mianqin/Code/knowledge/apps/cli/tests/test_main.py` | `apps/cli/tests/test_main.py` | `cli.md`, `cli-review-orchestration.md` |
| External page-to-card orchestration stays under `human_workspace` with flat `wiki_*` modules | `T02`, `T03` | `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_types.py`, `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_cursor.py`, `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_orchestrator.py`, `/Users/mianqin/Code/knowledge/human_workspace/pyproject.toml` | `human_workspace/tests/test_wiki_page_to_cards_cursor.py`, `human_workspace/tests/test_wiki_page_to_cards_orchestrator.py` | `knowledge-corpus-page-card-orchestration.md`, `04-repository-structure.md` |
| Input contract uses complete page records with `page_id`, `url`, `title`, and `clean_text` | `T02` | `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_types.py`, `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_cursor.py` | `human_workspace/tests/test_wiki_page_to_cards_cursor.py` | `knowledge-corpus-page-card-orchestration.md` |
| One page maps to one Cursor session and the page agent uses the existing write-card CLI command | `T02`, `T04` | `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_cursor.py` | `human_workspace/tests/test_wiki_page_to_cards_cursor.py`, `human_workspace/tests/test_wiki_page_to_cards_orchestrator.py` | `knowledge-corpus-page-card-orchestration.md` |
| Page-level result contains only `page_id` and `status` with statuses `completed | failed` | `T02`, `T03` | `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_types.py`, `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_orchestrator.py` | `human_workspace/tests/test_wiki_page_to_cards_cursor.py`, `human_workspace/tests/test_wiki_page_to_cards_orchestrator.py` | `knowledge-corpus-page-card-orchestration.md` |
| Processed marks occur only for completed pages and mean `handoff_complete` with deterministic `external_target_ref` | `T03`, `T04` | `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_orchestrator.py` | `human_workspace/tests/test_wiki_page_to_cards_orchestrator.py` | `knowledge-corpus-page-card-orchestration.md`, `knowledge-corpus.md` |
| First version has no automatic replay and no partial checkpointing | `T03` | `/Users/mianqin/Code/knowledge/human_workspace/wiki_page_to_cards_orchestrator.py` | `human_workspace/tests/test_wiki_page_to_cards_orchestrator.py` | `knowledge-corpus-page-card-orchestration.md` |

Coverage self-check:
- No behavior-changing design commitment in the current scope is left without a task, file, test, and spec update target.
- No task defaults to workaround behavior, silent failure, defensive masking, or duplicated submission logic.
- Each task has exactly one controller-owned finalization step at task end.

Plan complete and saved to `/Users/mianqin/Code/knowledge/.orbital/specs/plans/2026-04-05-knowledge-corpus-page-card-orchestration-plan.md`. Ready to execute?
