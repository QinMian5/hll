---
abstract: Project-owned source-pipeline orchestration design for source-agnostic intake, `page-to-card` extraction, and `card-review` fan-out through `job-queue-mcp`.
out_of_scope: Source-specific discovery/crawling policy, source-side processed bookkeeping, `job-queue-mcp` worker implementation details, final reviewed-card persistence, and taxonomy-classification behavior.
---

# Design: knowledge-corpus-page-card-orchestration

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted design for a project-owned source-pipeline app that accepts external source-processing configs or normalized units, submits `page-to-card` and `card-review` jobs through `job-queue-mcp`, and advances the workflow through one long-running orchestrator service.
- **Scope/Boundaries:** Covers source intake, minimal orchestration state, step contracts, queue interaction, and runtime/file ownership. Excludes source discovery policy, source-side bookkeeping, worker-side execution details, and final reviewed-card persistence.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository boundaries remain explicit, source-processing orchestration stays isolated from the online API runtime, environment behavior remains reproducible, and active specs capture only current accepted truth.
- **Detail Commitments:** The repository contains a project-owned `source_pipeline` app. `pipeline_intake` accepts one external config or normalized unit input and materializes minimal local orchestration state. `pipeline_runtime` continuously interacts with `job-queue-mcp`, stores only the linkage state that the queue cannot provide, and advances accepted step transitions. The `page-to-card` step returns a bare `cards[]` payload, including valid empty arrays. Each returned card fans out into one `card-review` job. `card-review` returns the existing six review dimensions. Source-side processed bookkeeping happens before work reaches this app and is outside this design.
- **Update Rule:** Requirement-level governance stays stable while this design owns source-pipeline runtime boundaries, minimal local state, step contracts, and file placement.

## Inputs & Outputs
- **Inputs:**
  - One external source-processing config submitted to `pipeline_intake`.
  - Optional pre-normalized source units submitted to `pipeline_intake`.
  - Access to `job-queue-mcp` producer and result surfaces.
- **Outputs:**
  - Persisted local linkage state for intake, unit tracking, and review handoff progress.
  - One `card-review` job submission per returned card.
  - Immediate handoff of accepted review results to downstream consumers.
- **Artifacts:**
  - `WorkflowRun`
  - `WorkflowUnit`
  - `CardReviewJob`
  - `SourceUnit`
  - `CardDraft`
  - `CardReviewResult`

## Design Approach
- **Approach:** Keep source adaptation separate from step orchestration. `pipeline_intake` owns external config ingestion and source-unit normalization. `pipeline_runtime` owns long-running orchestration state and all `job-queue-mcp` interactions. `page_to_card` and `card_review` own only step contracts. `pipeline_handoff` transfers accepted step outputs to the next step or downstream consumer without storing result payloads as durable business truth.
- **Key Elements:**
  - **Formal app boundary:** The source-processing runtime is a project app and is not a `human_workspace` script surface.
  - **Source-agnostic intake boundary:** `pipeline_intake` accepts one external config or normalized unit submission and materializes `WorkflowRun` plus `WorkflowUnit` rows. It does not select source pages, crawl source systems, or write source-side processed markers.
  - **Minimal local persistence:** The app persists only:
    - `workflow_runs` for one submitted orchestration request
    - `workflow_units` for one normalized unit plus its `page_to_card_job_id`
    - `card_review_jobs` for one fan-out card ordinal plus its `job_queue_job_id` and `handoff_done`
    It does not duplicate queue lifecycle state, accepted result payloads, or submission history that already exist in `job-queue-mcp`.
  - **Long-running orchestrator service:** `pipeline_runtime` runs as one dedicated process that continuously polls pending step jobs, reads accepted results, and advances state transitions.
  - **Queue-only execution boundary:** The project submits standardized step jobs to `job-queue-mcp` and consumes accepted results plus authoritative job views from the queue read surfaces. Worker-side execution mechanics are outside this app boundary.
  - **`SourceUnit` contract:** The normalized unit contains:
    - `source_kind`
    - `source_ref`
    - `title`
    - `content`
    - `metadata`
    `source_ref` is the source-owned opaque identifier. Source-specific bookkeeping is external to this app.
  - **`page-to-card` input contract:** The step input is one `SourceUnit`.
  - **`page-to-card` result contract:** The accepted result payload is a bare JSON array of `CardDraft`. Each `CardDraft` contains exactly:
    - `title`
    - `content`
    `[]` is a valid accepted result and means that the source unit produced no kept cards.
  - **No in-project execution assumptions:** The source-pipeline app does not define or own sessions, agents, prompts, tools, workspaces, or model selection on the worker side.
  - **`card-review` fan-out rule:** Each `CardDraft` returned by `page-to-card` produces one independent `card-review` job. Runtime bookkeeping may include row order or array index metadata, but that ordering is not a stable business identity.
  - **`card-review` input contract:** The step input is one `CardDraft`.
  - **`card-review` result contract:** The accepted result payload contains exactly:
    - `title_validity`
    - `title_content_alignment`
    - `title_style_validity`
    - `content_coherence`
    - `content_atomicity`
    - `content_latex_validity`
    The contract does not add a top-level aggregate `passed` field.
  - **Immediate handoff rule:** Accepted `card-review` results are forwarded through `pipeline_handoff` to the next step or downstream consumer and are not stored as durable project truth. The only persisted local flag is whether handoff already succeeded for a review job.
  - **Queue-as-truth rule:** The runtime rereads accepted results from `GET /results/{job_id}` and rereads current job state from the queue operator/result surfaces. It does not mirror accepted payloads, lifecycle states, leases, or submission history into local tables.
  - **No source discovery in runtime:** `pipeline_runtime` consumes only persisted `WorkflowUnit` state created by intake. Source selection remains outside the runtime.
  - **No final card persistence in current scope:** Current scope ends at accepted `card-review` handoff. Final reviewed-card storage is defined elsewhere.
- **Interactions:**
  1. An external caller submits one source-processing config to `pipeline_intake`.
  2. `pipeline_intake` validates the config, creates one `WorkflowRun`, and materializes the corresponding `WorkflowUnit` rows.
  3. `pipeline_runtime` selects units that do not yet have `page_to_card_job_id` and submits one `page-to-card` job per eligible unit to `job-queue-mcp`.
  4. `pipeline_runtime` polls the result surface until an accepted `page-to-card` payload is available or the job enters a terminal non-accepted state.
  5. `pipeline_runtime` rereads the accepted `cards[]` result, creates missing `CardReviewJob` rows by ordinal, and submits `card-review` jobs for rows that do not yet have `job_queue_job_id`.
  6. `pipeline_runtime` polls each `card-review` job until an accepted result is available or the job enters a terminal non-accepted state.
  7. `pipeline_handoff` forwards each accepted `card-review` result to the next step or downstream consumer and marks only `handoff_done=true` locally.

## File Placement
- The source-processing app is owned by `apps/source_pipeline`.
- The accepted first-version layout is:
  - `apps/source_pipeline/alembic`
  - `apps/source_pipeline/src/source_pipeline/config.py`
  - `apps/source_pipeline/src/source_pipeline/db/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_intake/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_runtime/`
  - `apps/source_pipeline/src/source_pipeline/page_to_card/`
  - `apps/source_pipeline/src/source_pipeline/card_review/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_handoff/`
  - `apps/source_pipeline/src/source_pipeline/entrypoints/orchestrator.py`
  - `apps/source_pipeline/tests/`
  - `infra/docker/source_pipeline/`
  - `infra/compose/docker-compose.base.yml` service entry for the dedicated `orchestrator` process

## Validation
- **Checks:**
  - Spec review confirms source intake, orchestration runtime, and step contracts are formal project-owned app boundaries rather than `human_workspace` scripts.
  - Contract tests verify `SourceUnit`, `CardDraft`, and `CardReviewResult` shapes.
  - Orchestrator tests verify `workflow_runs`, `workflow_units`, and `card_review_jobs` are sufficient for restart/resume behavior without mirroring queue lifecycle state.
  - Queue integration tests verify accepted `page-to-card` results fan out into one `card-review` job per returned card.
  - Handoff tests verify accepted review results are delivered downstream without durable review-payload persistence.
- **Evidence:**
  - Approved spec review with synchronized updates to impacted design docs.
  - Passing state-transition tests for intake, polling, fan-out, reread-from-queue behavior, and restart/resume behavior.
  - Passing contract tests for accepted `page-to-card` and `card-review` result shapes.
