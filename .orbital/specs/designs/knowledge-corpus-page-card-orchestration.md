---
abstract: Project-owned source-pipeline orchestration design for source-agnostic intake, card extraction, review, repair, and reviewed-card handoff.
out_of_scope: Source-specific discovery/crawling policy, source-side processed bookkeeping, `job-queue-mcp` worker implementation details, and taxonomy-classification behavior.
---

# Design: knowledge-corpus-page-card-orchestration

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted design for a project-owned source-pipeline app that accepts external source-processing configs or normalized units, submits `page-to-card`, `card-review`, and `card-repair` jobs through `job-queue-mcp`, and hands accepted cards to the knowledge ingestion HTTP boundary.
- **Scope/Boundaries:** Covers source intake, minimal orchestration state, step contracts, queue interaction, reviewed-card handoff, and runtime/file ownership. Excludes source discovery policy, source-side bookkeeping, worker-side execution details, and taxonomy classification.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository boundaries remain explicit, source-processing orchestration stays isolated from the online API runtime, environment behavior remains reproducible, and active specs capture only current accepted truth.
- **Detail Commitments:** The repository contains a project-owned `source_pipeline` app. `pipeline_intake` accepts one external config or normalized unit input and materializes minimal local orchestration state. `pipeline_runtime` continuously interacts with `job-queue-mcp`, stores only the linkage state that the queue cannot provide, and advances accepted step transitions. The `page-to-card` step returns an accepted payload object with a `cards` array, including valid empty arrays. Each returned card becomes a persisted `CardCandidate` with a `CardDraft` snapshot. Each candidate is reviewed independently. Passing review results hand the candidate to knowledge ingestion through `POST /api/v1/cards`. Failed review results create `card-repair` jobs whose repaired output cards become child candidates and re-enter review. Source pipeline owns its own dedicated PostgreSQL service, app-local Alembic lineage, and PostgreSQL-backed integration tests. Source-side processed bookkeeping happens before work reaches this app and is outside this design.
- **Update Rule:** Requirement-level governance stays stable while this design owns source-pipeline runtime boundaries, minimal local state, step contracts, and file placement.

## Inputs & Outputs
- **Inputs:**
  - One external source-processing config submitted to `pipeline_intake`.
  - Optional pre-normalized source units submitted to `pipeline_intake`.
  - Access to `job-queue-mcp` producer and result surfaces.
- **Outputs:**
  - Persisted local linkage state for intake, unit tracking, candidate lineage, review jobs, repair jobs, and ingestion handoff progress.
  - One `card-review` job submission per active candidate that has not yet been reviewed.
  - One `card-repair` job submission per rejected candidate that has not yet been repaired.
  - HTTP handoff of review-accepted candidates to knowledge ingestion.
- **Artifacts:**
  - `WorkflowRun`
  - `WorkflowUnit`
  - `CardCandidate`
  - `SourceUnit`
  - `CardDraft`
  - `CardReviewResult`
  - `CardRepairInput`
  - `CardRepairResult`

## Design Approach
- **Approach:** Keep source adaptation separate from step orchestration. `pipeline_intake` owns external config ingestion and source-unit normalization. `pipeline_runtime` owns long-running orchestration state and all `job-queue-mcp` interactions. `page_to_card`, `card_review`, and `card_repair` own only step contracts. `pipeline_handoff` transfers review-accepted card candidates to the knowledge ingestion HTTP boundary without writing the knowledge database directly.
- **Key Elements:**
  - **Formal app boundary:** The source-processing runtime is a project app and is not a `human_workspace` script surface.
  - **Dedicated database lifecycle:** `apps/source_pipeline` owns a dedicated PostgreSQL service and app-local migration lifecycle rather than sharing the online API database service.
  - **Source-agnostic intake boundary:** `pipeline_intake` accepts one external config or normalized unit submission and materializes `WorkflowRun` plus `WorkflowUnit` rows. It does not select source pages, crawl source systems, or write source-side processed markers.
  - **Minimal local persistence:** The app persists only:
    - `workflow_runs` for one submitted orchestration request
    - `workflow_units` for one normalized unit plus its `page_to_card_job_id`
    - `card_candidates` for candidate lineage, one `CardDraft` snapshot, review job linkage, repair job linkage, and ingestion handoff completion
    It does not duplicate queue lifecycle state, accepted result payloads, or submission history that already exist in `job-queue-mcp`.
  - **Candidate-centric orchestration:** A `CardCandidate` is the durable source-pipeline identity for one candidate card. It stores one `CardDraft` snapshot plus workflow-local lineage and job-linkage fields. Queue payloads and results continue to use `CardDraft` for card content.
  - **`CardCandidate` persistence shape:** Each candidate records:
    - `id`
    - `workflow_unit_id`
    - `parent_candidate_id`
    - `card_payload`
    - `origin_step`
    - `origin_job_id`
    - `origin_ordinal`
    - `review_job_id`
    - `repair_job_id`
    - `ingestion_handoff_done`
    - `created_at`
  - **Candidate state derivation:** Candidate state is derived from job-linkage fields, accepted queue results, and `ingestion_handoff_done`. The first version does not require a separate candidate status enum.
  - **Long-running orchestrator service:** `pipeline_runtime` runs as one dedicated process that continuously polls pending step jobs, reads accepted results, and advances state transitions.
  - **Queue-only execution boundary:** The project submits standardized step jobs to `job-queue-mcp` and consumes accepted results plus authoritative job views from the queue read surfaces. Worker-side execution mechanics are outside this app boundary.
  - **App-local configuration contract:** The app owns `SOURCE_PIPELINE_DATABASE_URL` and `SOURCE_PIPELINE_MIGRATION_DATABASE_URL` and must not reuse API or knowledge-corpus database URL names.
  - **Knowledge ingestion handoff configuration:** The app owns source-pipeline-specific knowledge API configuration, including the knowledge API base URL used for accepted-card handoff. Authentication settings for the knowledge API are source-pipeline configuration when the target knowledge API requires authentication.
  - **Job-queue authentication boundary:** The runtime authenticates to `job-queue-mcp` with a Logto machine-to-machine client-credentials flow. It stores client credentials as environment configuration, requests short-lived access tokens at runtime, and does not store static producer or results-reader bearer tokens.
  - **Production network boundary:** In production, the orchestrator joins the shared `proxy` network and reaches `job-queue-mcp` through the queue stack's reverse-proxy hostnames. It does not join the queue stack's private backend network or rely on container-name shortcuts.
  - **`SourceUnit` contract:** The normalized unit contains:
    - `source_kind`
    - `source_ref`
    - `title`
    - `content`
    - `metadata`
    `source_ref` is the source-owned opaque identifier. Source-specific bookkeeping is external to this app.
  - **`page-to-card` queue name:** The page-to-card step submits jobs to the `page_to_card` queue.
  - **`page-to-card` input contract:** The step input is one `SourceUnit`.
  - **`page-to-card` task guidance:** The `page-to-card` job instruction carries the extraction policy and atomic-card selection guidance. That instruction remains task-specific and does not carry transport-generic worker protocol rules.
  - **`page-to-card` result contract:** The accepted result payload is a JSON object with one required field:
    - `cards`
    The `cards` field is an array of `CardDraft`. Each `CardDraft` contains exactly:
    - `title`
    - `content`
    `{ "cards": [] }` is a valid accepted result and means that the source unit produced no kept cards.
  - **No in-project execution assumptions:** The source-pipeline app does not define or own sessions, agents, prompts, tools, workspaces, or model selection on the worker side.
  - **`page-to-card` candidate rule:** Each `CardDraft` returned by `page-to-card` creates one initial `CardCandidate`. Runtime bookkeeping may include array index metadata, but array order is not a stable business identity.
  - **`card-review` fan-out rule:** Each `CardCandidate` without a review job produces one independent `card-review` job.
  - **`card-review` queue name:** The card-review step submits jobs to the `card_review` queue.
  - **`card-review` input contract:** The step input is one `CardDraft`.
  - **`card-review` task guidance split:** The `card-review` job instruction stays minimal and task-framing only. The detailed six-dimension review semantics live in the Pydantic-authored output-schema field descriptions exported with the job contract.
  - **`card-review` result contract:** The accepted result payload contains exactly:
    - `title_validity`
    - `title_content_alignment`
    - `title_style_validity`
    - `content_coherence`
    - `content_atomicity`
    - `content_latex_validity`
    The contract does not add a top-level aggregate `passed` field.
  - **Review pass rule:** A `card-review` result passes only when all six dimensions have `passed=true`.
  - **Accepted-card handoff rule:** Passing `card-review` results are forwarded through `pipeline_handoff` to the knowledge ingestion HTTP endpoint `POST /api/v1/cards` with only the candidate title and content in the request body. Every handoff request for one `CardCandidate` carries the same stable `Idempotency-Key` header derived from source-pipeline candidate identity. `pipeline_handoff` marks `ingestion_handoff_done=true` only after the knowledge API accepts the request with `202 Accepted`.
  - **Rejected-card repair rule:** Failed `card-review` results create one `card-repair` job for the rejected candidate when no repair job exists for that candidate.
  - **`card-repair` queue name:** The repair step submits jobs to the `card_repair` queue.
  - **`card-repair` input contract:** The step input is one object with:
    - `card`: the rejected `CardDraft`
    - `review`: the accepted `CardReviewResult`
  - **`card-repair` task guidance:** The `card-repair` instruction explains how to repair the candidate using only the rejected card and review result. It includes the six card-quality dimensions so the worker can repair toward the same standard enforced by review. The instruction does not include transport-generic worker protocol rules.
  - **`card-repair` result contract:** The accepted result payload is a JSON object with one required field:
    - `cards`
    The `cards` field is an array of `CardDraft`. `{ "cards": [] }` is a valid accepted result and means the rejected candidate cannot be repaired from the provided card and review result.
  - **Repair child-candidate rule:** Each `CardDraft` returned by `card-repair` creates one child `CardCandidate` with `parent_candidate_id` pointing to the rejected candidate. Each child candidate re-enters `card-review`.
  - **Repair loop rule:** The first version does not set a maximum repair-attempt count. A lineage stops only when a candidate passes review and completes ingestion handoff, a repair result returns no cards, or a required queue job reaches a terminal non-accepted state.
  - **Shared quality criteria rule:** The six card-quality criteria are maintained as shared source-pipeline task guidance and projected consistently into page extraction, card review schema descriptions, and card repair instructions.
  - **Handoff retry rule:** If knowledge ingestion handoff fails before `202 Accepted`, `ingestion_handoff_done` remains false and a later orchestrator tick retries the handoff with the same stable `Idempotency-Key`.
  - **Candidate idempotency rule:** Repeated ticks must not duplicate review jobs, repair jobs, ingestion handoffs, or child candidates. Child-candidate creation is idempotent for one parent candidate, one repair job, and one repair-result ordinal. Knowledge ingestion treats repeated `POST /api/v1/cards` requests carrying the same `Idempotency-Key` as the same logical accepted submission, so ambiguous network failures do not materialize duplicate cards.
  - **Queue-as-truth rule:** The runtime rereads accepted results from `GET /results/{job_id}` and rereads current job state from the queue operator/result surfaces. It does not mirror accepted payloads, lifecycle states, leases, or submission history into local tables.
  - **No source discovery in runtime:** `pipeline_runtime` consumes only persisted `WorkflowUnit` state created by intake. Source selection remains outside the runtime.
  - **Knowledge persistence boundary:** Source pipeline does not write knowledge graph tables, compute embeddings, create edges, update adjacency, or assign taxonomy. Accepted card persistence is performed by the knowledge ingestion API and worker runtime.
  - **Card quality criteria:** Page extraction, card review, and card repair share these criteria:
    - `title_validity`: the title is unambiguous, precisely scoped, and independently understandable without requiring additional context.
    - `title_content_alignment`: the title accurately and sufficiently indicates the actual topic discussed by the content.
    - `title_style_validity`: the title follows `<subject>` or `<subject> (<domain>)`; `<subject>` is preferred by default; the parenthesized domain is used only for minimal disambiguation; the title uses Title Case with minor function words such as `a`, `an`, `the`, `of`, and `in` lowercase unless they begin the title; full sentences, definition-like phrases, colon-separated explanatory labels, and unnecessary qualifiers are invalid.
    - `content_coherence`: the content is self-contained and self-explanatory given standard domain terminology, without missing context, hidden assumptions, unresolved references, or implicit external prerequisites that should be stated.
    - `content_atomicity`: the content represents exactly one indivisible knowledge unit; content that can be meaningfully split into multiple independent knowledge units must be split into separate cards when a repair step can do so using the provided input.
    - `content_latex_validity`: LaTeX math uses `\(` and `\)` for inline formulas and `\[` and `\]` for display formulas; `$`, `$$`, mismatched delimiters, and malformed LaTeX syntax are invalid.
- **Interactions:**
  1. An external caller submits one source-processing config to `pipeline_intake`.
  2. `pipeline_intake` validates the config, creates one `WorkflowRun`, and materializes the corresponding `WorkflowUnit` rows.
  3. `pipeline_runtime` selects units that do not yet have `page_to_card_job_id` and submits one `page-to-card` job per eligible unit to `job-queue-mcp`.
  4. `pipeline_runtime` polls the result surface until an accepted `page-to-card` payload is available or the job enters a terminal non-accepted state.
  5. `pipeline_runtime` rereads the accepted `result_payload["cards"]` result and creates missing initial `CardCandidate` rows by page result ordinal.
  6. `pipeline_runtime` submits one `card-review` job for each candidate that lacks `review_job_id`.
  7. `pipeline_runtime` polls each `card-review` job until an accepted result is available or the job enters a terminal non-accepted state.
  8. When all review dimensions pass, `pipeline_handoff` posts the candidate title and content to `POST /api/v1/cards` with a stable `Idempotency-Key` and marks `ingestion_handoff_done=true` after `202 Accepted`.
  9. When any review dimension fails, `pipeline_runtime` submits one `card-repair` job for the candidate when no repair job exists.
  10. `pipeline_runtime` polls each `card-repair` job until an accepted result is available or the job enters a terminal non-accepted state.
  11. `pipeline_runtime` creates child `CardCandidate` rows for each repaired card returned by `card-repair`.
  12. Child candidates re-enter the same review flow.

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
  - `apps/source_pipeline/src/source_pipeline/card_repair/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_handoff/`
  - `apps/source_pipeline/src/source_pipeline/entrypoints/orchestrator.py`
  - `apps/source_pipeline/tests/`
  - `infra/docker/source_pipeline/`
  - `infra/compose/docker-compose.base.yml` service entry for the dedicated `orchestrator` process

## Validation
- **Checks:**
  - Spec review confirms source intake, orchestration runtime, and step contracts are formal project-owned app boundaries rather than `human_workspace` scripts.
  - Contract tests verify `SourceUnit`, `CardDraft`, `CardReviewResult`, `CardRepairInput`, and `CardRepairResult` shapes.
  - Instruction tests verify page extraction, card review, and card repair share the same six card-quality criteria without duplicating transport-generic worker protocol instructions.
  - PostgreSQL-backed integration tests verify `workflow_runs`, `workflow_units`, and `card_candidates` are sufficient for restart/resume behavior without mirroring queue lifecycle state.
  - Queue integration tests verify accepted `page-to-card` results create candidates and fan out into one `card-review` job per candidate.
  - Runtime tests verify failed review results submit `card-repair` jobs and accepted repair results create zero or more child candidates that re-enter review.
  - Runtime tests verify `page-to-card`, `card-review`, and `card-repair` terminal non-accepted states stop automatic fan-out and do not create downstream candidates or handoffs.
  - Runtime tests verify `card-repair` accepted results with `cards=[]` stop the candidate lineage without creating child candidates.
  - Handoff tests verify passing review results call `POST /api/v1/cards`, mark completion only after `202 Accepted`, and retry failed handoff attempts with the same `Idempotency-Key`.
  - Idempotency tests verify repeated ticks do not duplicate review jobs, repair jobs, child candidates, or ingestion handoffs.
  - Integration tests verify knowledge ingestion deduplicates repeated accepted-card handoffs with the same `Idempotency-Key`, including timeout or connection-loss retries after the server accepted the original request.
- **Evidence:**
  - Approved spec review with synchronized updates to impacted design docs.
  - Passing PostgreSQL-backed state-transition tests for intake, polling, candidate creation, repair loops, reread-from-queue behavior, ingestion handoff, and restart/resume behavior.
  - Passing contract tests for accepted `page-to-card`, `card-review`, and `card-repair` result shapes.
