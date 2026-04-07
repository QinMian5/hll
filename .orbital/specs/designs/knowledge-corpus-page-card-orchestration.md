---
abstract: External page-to-card orchestration design for running one Cursor session per source page and writing reviewed cards through the existing write-card CLI command backed by the shared reviewed-submission boundary owned by apps/cli.
out_of_scope: Page discovery strategy, topic filtering policy, online API runtime ownership, card-level checkpoint persistence, and changes to the existing single-card CLI contract.
---

# Design: knowledge-corpus-page-card-orchestration

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted design for an external orchestration library that consumes page records from `knowledge_corpus`, runs one Cursor session per page, extracts multiple atomic knowledge cards within that page session, and writes each card through the existing write-card CLI command backed by the shared reviewed-submission boundary owned by `apps/cli`.
- **Scope/Boundaries:** Covers orchestration boundaries, page/session contracts, Cursor page-agent behavior, page-level concurrency, processed-mark semantics, and file placement. Excludes page discovery, topic filtering, card-level checkpointing, direct database writes for knowledge cards, and changes to `apps/cli` review semantics.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository boundaries remain explicit, offline orchestration stays outside online runtime ownership, environment behavior remains reproducible, and behavior-changing design updates keep active specs current.
- **Detail Commitments:** The repository contains an external orchestration library under `human_workspace/` that accepts complete page records, runs a bounded number of concurrent page sessions, gives each page session a single Cursor agent context, and routes all card writes through the existing write-card CLI command owned by `apps/cli`, whose behavior is backed by a shared reviewed-submission Python entrypoint. A page is marked processed only after the page session completes successfully at the reviewed handoff boundary.
- **Update Rule:** Requirement-level constraints remain stable while this design owns orchestration-facing file placement, page/session contracts, tool boundaries, concurrency semantics, and processed-mark rules.

## Inputs & Outputs
- **Inputs:**
  - A sequence of complete page records.
  - A maximum concurrent worker count.
  - Runtime access to:
    - Cursor Agent headless execution
    - the existing write-card CLI command from `apps/cli`
    - the `knowledge_corpus` processed-mark library interface
- **Outputs:**
  - One page-level result per input page.
  - Zero or more reviewed knowledge-card submissions issued through the existing write-card CLI command backed by `apps/cli`.
  - Processed-document marks for every page whose outer page attempt finishes, regardless of whether the final page-agent result can be parsed successfully.
- **Artifacts:**
  - `PageRecord`
  - `PageResult`
  - `PagesOrchestrator`
  - `PageAgentRunner`
  - write-card adapter

## Design Approach
- **Approach:** Keep the new workflow outside application ownership boundaries and model it as a page-oriented orchestration library. The orchestrator receives complete page records from an external caller, schedules page-level workers, and lets each worker run one autonomous Cursor page session. Inside that page session, Cursor reads the page, decides when enough atomic cards have been extracted, and repeatedly invokes the existing write-card CLI command from `apps/cli`, whose behavior is backed by the shared reviewed-submission Python entrypoint.
- **Key Elements:**
  - **External workflow boundary:** The orchestration library lives under `human_workspace/` and is not part of `apps/knowledge_corpus` or `apps/cli`.
  - **Input contract:** The library accepts complete page records rather than IDs, search queries, or provider definitions. The minimum accepted fields are:
    - `page_id`
    - `url`
    - `title`
    - `clean_text`
  - **Library-first entrypoint:** The primary interface is an importable Python function rather than a first-version CLI wrapper.
  - **Fixed runtime entrypoints:** Dedicated external runtime scripts under `human_workspace/` provide operator-facing commands for both curated STEM-title ingestion and science query-batch ingestion. The query-batch mode loads YAML-configured full-text searches, selects unprocessed pages through `knowledge_corpus.wikipedia.search.search_documents(...)`, deduplicates by `page_id`, runs the orchestrator with `max_workers=8`, and displays page-count progress with `rich`.
  - **Page-scoped agent contract:** Each page is handled by exactly one Cursor session. The session owns page-local reasoning and decides when no more worthwhile atomic cards remain.
  - **Autonomous in-session extraction:** The orchestrator does not drive a card-by-card outer loop. The Cursor page session first plans which cards should be extracted from the page, then submits them sequentially within that same session.
  - **Soft card-count target:** The page session aims to extract about 10 of the most important atomic knowledge cards from a page. This is a soft target rather than a hard cap: shorter pages may yield fewer cards, and longer pages should prioritize the most important and most foundational knowledge instead of trying to exhaustively cover every detail.
  - **Single write command:** The page session uses the existing write-card CLI command from `apps/cli` rather than reimplementing review/submission logic or introducing a new tool surface.
  - **Card contract inside the page session:** The page session treats each card as one self-contained atomic knowledge unit with exactly two fields, `title` and `content`, and plans candidate cards against the same five review dimensions enforced by `apps/cli`:
    - `title_validity`
    - `title_content_alignment`
    - `title_style_validity`
    - `content_coherence`
    - `content_atomicity`
    - `content_latex_validity`
    Card titles must follow either `<subject>` or `<subject> (<domain>)`, with the parenthesized domain used only for minimal disambiguation.
  - **Shared submission-function reuse:** The write-card CLI command remains a thin wrapper over the same reviewed-submission Python function, so terminal use and any future import-based use stay behaviorally aligned.
  - **Sequential submission rule:** The page session submits one planned card at a time and does not begin the next planned card until the current card has returned `accepted`.
  - **Rejected-card handling rule:** If the write-card command rejects a candidate card, the page session revises that same candidate against the rejection details and retries it. If the candidate cannot be revised into an acceptable card, the page session ends as `failed` rather than silently skipping that planned card.
  - **Write-card command result contract:** The page session treats the existing write-card CLI command as authoritative and consumes its current terminal result contract:
    - `accepted`: exit code `0` with stdout JSON containing `{"result":"passed"}`
    - `rejected`: exit code `1` with stdout JSON containing `{"result":"failed","failures":...}`
    - `runtime_error`: any other terminal outcome, including malformed stdout or command failure before a valid accepted/rejected payload is produced
  - **Minimal page result contract:** The page-level result always contains:
    - `page_id`
    - `completed`
    - `reason`
  - **Page-agent return channel:** The Cursor page session returns a JSON object that matches the page-specific `PageResult` schema exactly. The local runner injects a `TypeAdapter`-derived JSON Schema into the prompt and validates the returned JSON against the same Pydantic contract.
  - **Completion contract:** `completed` is `true` only when the page session has finished successfully and every kept card has already been accepted by the reviewed write-card command. `completed` is `false` when the page session cannot be completed.
  - **Reason contract:** `reason` must be `null` when `completed=true` and must be a concise non-empty failure reason when `completed=false`.
  - **Concurrency model:** The orchestrator uses a bounded thread pool. Each worker owns one page at a time and waits primarily on external Cursor subprocesses plus write-card CLI invocations rather than CPU-bound Python work.
  - **Processed-mark rule:** A page is marked in `wikipedia.processed_documents` after the outer page attempt finishes, regardless of whether the final page-agent result can be parsed into `PageResult`.
  - **Processed semantic meaning:** For this workflow, `processed` means `attempt_finished`: the external page attempt has run to completion and will not be retried by default. This processed mark no longer depends on successful parsing of the page-agent's final structured result.
  - **Processed-mark reference contract:** When a page reaches `completed`, the orchestrator records a deterministic page-scoped `external_target_ref` in the form `cursor-page-agent:wikipedia:<page_id>`.
  - **Failure rule:** If a page session fails at any point, including after some cards have already been written, the page result is `failed`. The page is still marked processed once the outer page attempt finishes.
  - **No automatic replay:** First version does not automatically rerun failed pages. A failed page ends the current workflow attempt immediately.
  - **No partial checkpointing:** First version does not store page-internal card progress or partial completion state.
  - **Knowledge-corpus integration boundary:** Processed marking uses the existing `knowledge_corpus.wikipedia.service.mark_document_processed(...)` helper rather than direct SQL or a parallel status store.
- **Interactions:**
  1. An external caller constructs a sequence of `PageRecord` values.
  2. The caller invokes the orchestration library with the page sequence and `max_workers`.
  3. The orchestrator schedules pages across a bounded thread pool.
  4. Each worker starts one Cursor page session for one page.
  5. Inside the page session, Cursor reads the page, plans the candidate cards, and invokes the existing write-card CLI command sequentially for those atomic card submissions.
  6. When the page session determines that extraction is complete, it returns a `PageResult` with `page_id`, `completed`, and `reason`.
  7. If `completed=true`, the orchestrator marks that page processed through `knowledge_corpus`.
  8. If `completed=false`, the orchestrator returns the failed page result, does not mark the page processed, and does not automatically retry that page.

## File Placement
- The orchestration module is owned by `human_workspace/`.
- The first-version implementation uses three focused files:
  - `human_workspace/wiki_page_to_cards_types.py` for page/result data contracts
  - `human_workspace/wiki_page_to_cards_cursor.py` for one-page Cursor session execution plus write-card CLI integration
  - `human_workspace/wiki_page_to_cards_orchestrator.py` for top-level `run_pages(...)` orchestration plus processed marking
  - `human_workspace/run_stem_ingestion.py` for fixed STEM candidate selection plus operator-facing ingestion progress UI
  - `human_workspace/science-query-batches.yaml` for ordered science-oriented search batches
  - `human_workspace/run_science_ingestion.py` for YAML-driven science query-batch ingestion plus operator-facing ingestion progress UI

## Validation
- **Checks:**
  - Spec review confirms orchestration remains outside `apps/knowledge_corpus` and `apps/cli` ownership boundaries.
  - Contract tests verify that the orchestration entrypoint accepts complete page records and returns `page_id + completed + reason` with the correct success/failure reason contract.
  - Session-runner tests verify that one page maps to one Cursor session and that card writes flow through the existing write-card CLI command.
  - Processed-mark tests verify that every finished page attempt calls `mark_document_processed(...)`.
  - Failure-isolation tests verify that one failed page does not stop other page workers from completing.
- **Evidence:**
  - Approved spec review with synchronized updates to impacted design documents.
  - Passing orchestration tests for page scheduling, page-result contract shape, and processed-mark semantics.
  - Passing integration checks demonstrating reviewed card writes from within a page-scoped Cursor session through the existing write-card CLI command.
