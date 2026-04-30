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
- **Purpose:** Define the accepted design for a project-owned source-pipeline app that accepts external source-processing configs or normalized units, submits `page-to-card`, `card-review`, and `card-repair` jobs through `job-queue-mcp`, receives queue result notifications, and hands accepted cards to the knowledge ingestion HTTP boundary.
- **Scope/Boundaries:** Covers source intake, minimal orchestration state, step contracts, queue interaction, webhook event intake, reviewed-card handoff, and runtime/file ownership. Excludes source discovery policy, source-side bookkeeping, worker-side execution details, and taxonomy classification.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository boundaries remain explicit, source-processing orchestration stays isolated from the online API runtime, environment behavior remains reproducible, and active specs capture only current accepted truth.
- **Detail Commitments:** The repository contains a project-owned `source_pipeline` app. `pipeline_intake` accepts one external config or normalized unit input and materializes minimal local orchestration state. `pipeline_runtime` interacts with `job-queue-mcp`, stores only the linkage state and local notification state that the queue cannot provide, and advances accepted step transitions after local queue-result events or low-frequency reconcile identify relevant jobs. The `page-to-card` step returns an accepted payload object with a `cards` array, including valid empty arrays. Each returned card becomes a persisted `CardCandidate` with a `CardDraft` snapshot. Each candidate is reviewed independently. Passing review results hand the candidate to knowledge ingestion through `POST /api/v1/cards`. Failed review results create `card-repair` jobs whose repaired output cards become child candidates and re-enter review. Source pipeline owns its own dedicated PostgreSQL service, app-local Alembic lineage, source-pipeline webhook receiver service, and PostgreSQL-backed integration tests. Source-side processed bookkeeping happens before work reaches this app and is outside this design.
- **Update Rule:** Requirement-level governance stays stable while this design owns source-pipeline runtime boundaries, minimal local state, step contracts, and file placement.

## Inputs & Outputs
- **Inputs:**
  - One external source-processing config submitted to `pipeline_intake`.
  - Optional pre-normalized source units submitted to `pipeline_intake`.
  - Access to `job-queue-mcp` producer and result surfaces.
  - Queue-level notification events delivered by `job-queue-mcp` for source-pipeline queues.
- **Outputs:**
  - Persisted local linkage state for intake, unit tracking, candidate lineage, review jobs, repair jobs, and ingestion handoff progress.
  - Persisted local webhook event state for idempotent queue-result notification handling.
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
  - `JobQueueWebhookEvent`

## Design Approach
- **Approach:** Keep source adaptation, webhook intake, and step orchestration separate. `pipeline_intake` owns external config ingestion and source-unit normalization. The source-pipeline webhook receiver owns authenticated queue-result event intake and local event persistence. `pipeline_runtime` owns long-running orchestration state and all state advancement from local queue-result events, low-frequency reconcile, and `job-queue-mcp` result reads. `page_to_card`, `card_review`, and `card_repair` own only step contracts. `pipeline_handoff` transfers review-accepted card candidates to the knowledge ingestion HTTP boundary without writing the knowledge database directly.
- **Key Elements:**
  - **Formal app boundary:** The source-processing runtime is a project app and is not a `human_workspace` script surface.
  - **Dedicated database lifecycle:** `apps/source_pipeline` owns a dedicated PostgreSQL service and app-local migration lifecycle rather than sharing the online API database service.
  - **Source-agnostic intake boundary:** `pipeline_intake` accepts one external config or normalized unit submission and materializes `WorkflowRun` plus `WorkflowUnit` rows. It does not select source pages, crawl source systems, or write source-side processed markers.
  - **Minimal local persistence:** The app persists only:
    - `workflow_runs` for one submitted orchestration request and its source config metadata, without duplicating normalized unit payloads
    - `workflow_units` for one normalized unit plus its `page_to_card_job_id` and page-step terminal checkpoint
    - `card_candidates` for candidate lineage, one `CardDraft` snapshot, review job linkage, review terminal checkpoint, repair job linkage, repair terminal checkpoint, and ingestion handoff completion
    - `job_queue_webhook_events` for idempotent notification intake, processing state, and local wakeup/reconcile coordination
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
    - `review_terminal_state`
    - `repair_job_id`
    - `repair_terminal_state`
    - `ingestion_handoff_done`
    - `created_at`
  - **Candidate state derivation:** Candidate state is derived from job-linkage fields, accepted queue results, and `ingestion_handoff_done`. The first version does not require a separate candidate status enum.
  - **Source-pipeline webhook receiver service:** The project owns a dedicated source-pipeline receiver service for `job-queue-mcp` notifications. The receiver authenticates incoming webhook calls, persists events through repository-owned atomic idempotent insertion, and emits a local database-backed wakeup for `pipeline_runtime`.
  - **Receiver non-processing rule:** The webhook receiver does not create candidates, submit follow-up jobs, perform knowledge ingestion handoff, or read accepted result payloads. It returns after authenticated idempotent event persistence.
  - **Long-running orchestrator service:** `pipeline_runtime` runs as one dedicated process that waits on local webhook event notifications, processes local pending queue-result events, performs low-frequency reconcile for outstanding job linkages, reads accepted results from `job-queue-mcp` when needed, and advances state transitions.
  - **Queue-only execution boundary:** The project submits standardized step jobs to `job-queue-mcp` and consumes queue notifications plus authoritative accepted results from the queue read surfaces. Worker-side execution mechanics are outside this app boundary.
  - **Producer/result-reader SDK boundary:** The source-pipeline runtime uses the upstream `job_queue_mcp_client.producer.AsyncClient` and `job_queue_mcp_client.auth.ClientCredentialsTokenProvider` public facades directly. Source-pipeline modules own task instructions, output schemas, payload construction, metadata construction, local persistence, result validation, and state transitions. The upstream SDK owns job-queue HTTP contract calls and machine-to-machine token acquisition.
  - **App-local configuration contract:** The app owns `SOURCE_PIPELINE_DATABASE_URL` and `SOURCE_PIPELINE_MIGRATION_DATABASE_URL` and must not reuse API or knowledge-corpus database URL names.
  - **Knowledge ingestion handoff configuration:** The app owns source-pipeline-specific knowledge API configuration, including the knowledge API base URL used for accepted-card handoff. Authentication settings for the knowledge API are source-pipeline configuration when the target knowledge API requires authentication.
  - **Job-queue authentication boundary:** The runtime authenticates to `job-queue-mcp` with a Logto machine-to-machine client-credentials flow. It stores client credentials as environment configuration, requests short-lived access tokens at runtime, and does not store static producer or results-reader bearer tokens.
  - **Webhook receiver authentication boundary:** The source-pipeline webhook receiver authenticates incoming `job-queue-mcp` webhook calls using the `knowledge` Logto authority. `job-queue-mcp` acts as a machine-to-machine client of `knowledge` Logto for webhook delivery. The receiver validates issuer, audience/resource, expiry, and configured webhook caller client identity before persisting an event.
  - **Webhook-auth ownership boundary:** Source-pipeline webhook receiver authentication remains receiver-owned. The job-queue producer/result-reader SDK is not the authority for incoming delivery-token validation.
  - **Production network boundary:** In production, the orchestrator joins the shared `proxy` network and reaches `job-queue-mcp` through the queue stack's reverse-proxy hostnames. It does not join the queue stack's private backend network or rely on container-name shortcuts.
  - **Webhook exposure boundary:** In production, the project-local app gateway exposes only the source-pipeline webhook receiver path needed by `job-queue-mcp`. The receiver is not the online knowledge API and does not expose source-pipeline administration or result-read endpoints.
  - **`SourceUnit` contract:** The normalized unit contains:
    - `source_kind`
    - `source_ref`
    - `title`
    - `content`
    - `metadata`
    `source_ref` is the source-owned opaque identifier. Source-specific bookkeeping is external to this app.
  - **`page-to-card` queue name:** The page-to-card step submits jobs to the `page_to_card` queue.
  - **`page-to-card` input contract:** The step input is one `SourceUnit`.
  - **`page-to-card` task guidance:** The `page-to-card` job instruction carries the extraction policy and focused, compact, context-sufficient card selection guidance. That instruction remains task-specific and does not carry transport-generic worker protocol rules.
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
  - **`card-review` task guidance:** The `card-review` job instruction carries the unified card quality standard and asks for one overall judgment. The instruction remains task-specific and does not carry transport-generic worker protocol rules.
  - **`card-review` result contract:** The accepted result payload contains exactly:
    - `passed`
    - `reason`
    `passed` is the overall judgment for the candidate card. `reason` explains why the card failed and is required when `passed=false`.
  - **Review pass rule:** A `card-review` result passes when `passed=true`.
  - **Accepted-card handoff rule:** Passing `card-review` results are forwarded through `pipeline_handoff` to the knowledge ingestion HTTP endpoint `POST /api/v1/cards` with only the candidate title and content in the request body. Every handoff request for one `CardCandidate` carries the same stable `Idempotency-Key` header derived from source-pipeline candidate identity. `pipeline_handoff` marks `ingestion_handoff_done=true` only after the knowledge API accepts the request with `202 Accepted`.
  - **Rejected-card repair rule:** Failed `card-review` results create one `card-repair` job for the rejected candidate when no repair job exists for that candidate.
  - **`card-repair` queue name:** The repair step submits jobs to the `card_repair` queue.
  - **`card-repair` input contract:** The step input is one object with:
    - `card`: the rejected `CardDraft`
    - `review`: the accepted `CardReviewResult`
  - **`card-repair` task guidance:** The `card-repair` instruction explains how to repair the candidate using only the rejected card, review result, and review reason. It includes the unified card quality standard so the worker can repair toward focused, compact, context-sufficient card drafts under the same standard enforced by review. The instruction does not include transport-generic worker protocol rules.
  - **`card-repair` result contract:** The accepted result payload is a JSON object with one required field:
    - `cards`
    The `cards` field is an array of `CardDraft`. `{ "cards": [] }` is a valid accepted result and means the rejected candidate cannot be repaired from the provided card and review result.
  - **Repair child-candidate rule:** Each `CardDraft` returned by `card-repair` creates one child `CardCandidate` with `parent_candidate_id` pointing to the rejected candidate. Each child candidate re-enters `card-review`.
  - **Repair loop rule:** The first version does not set a maximum repair-attempt count. A lineage stops only when a candidate passes review and completes ingestion handoff, a repair result returns no cards, or a required queue job reaches a terminal non-accepted state.
  - **Shared quality standard rule:** One unified card-quality standard is maintained as shared source-pipeline task guidance and projected consistently into page extraction, card review instructions, and card repair instructions.
  - **Handoff retry rule:** If knowledge ingestion handoff fails before `202 Accepted`, `ingestion_handoff_done` remains false and a later orchestrator tick retries the handoff with the same stable `Idempotency-Key`.
  - **Candidate idempotency rule:** Repeated ticks must not duplicate review jobs, repair jobs, ingestion handoffs, or child candidates. Child-candidate creation is idempotent for one parent candidate, one repair job, and one repair-result ordinal. Knowledge ingestion treats repeated `POST /api/v1/cards` requests carrying the same `Idempotency-Key` as the same logical accepted submission, so ambiguous network failures do not materialize duplicate cards.
  - **Queue-as-truth rule:** Local webhook events are notification triggers only. The runtime rereads accepted results from `GET /results/{job_id}` and rereads current job state from the queue operator/result surfaces during reconcile. It stores only the terminal non-accepted checkpoint needed to stop repeated local polling and does not mirror accepted payloads, full lifecycle history, leases, or submission history into local tables.
  - **Webhook idempotency rule:** Each incoming webhook event carries a stable event identity. The receiver records each event id once through atomic insert-on-conflict semantics and treats duplicate deliveries as successful repeats without creating duplicate local work.
  - **Local wakeup rule:** Persisting a new webhook event wakes `pipeline_runtime` through a local database-backed notification or queue. The runtime owns event processing and marks local events processed only after the matching source-pipeline state advancement has completed.
  - **Low-frequency reconcile rule:** `pipeline_runtime` keeps a low-frequency reconcile path for outstanding job linkages. Reconcile is a compensation path for missed notifications, configuration errors, or exhausted remote delivery retries; it is not the primary result-consumption path.
  - **No source discovery in runtime:** `pipeline_runtime` consumes only persisted `WorkflowUnit` state created by intake. Source selection remains outside the runtime.
  - **Knowledge persistence boundary:** Source pipeline does not write knowledge graph tables, compute embeddings, create edges, update adjacency, or assign taxonomy. Accepted card persistence is performed by the knowledge ingestion API and worker runtime.
  - **Card quality standard:** Page extraction, card review, and card repair share this standard:
    - Each card represents one knowledge unit.
    - The title follows Title Case and includes no qualifiers beyond minimal disambiguation. If the same term could reasonably refer to different meanings across domains, the title uses `<Subject> (<Domain>)`.
    - The title is self-descriptive enough for readers to infer the main topic without reading the content. Each card maintains a one-to-one mapping between title and content.
    - Given standard domain terminology, the content is focused, compact, self-contained, and self-explanatory. It does not rely on hidden assumptions, external prerequisites, missing context, hidden dependencies, or unresolved references.
    - Definitions, qualifiers, mechanisms, examples, or implications may stay together when they help readers understand the same knowledge unit.
    - LaTeX math uses `\(` and `\)` for inline formulas and `\[` and `\]` for display formulas. Malformed LaTeX and `$` or `$$` delimiters are invalid.
- **Interactions:**
  1. An external caller submits one source-processing config to `pipeline_intake`.
  2. `pipeline_intake` validates the config, creates one `WorkflowRun`, and materializes the corresponding `WorkflowUnit` rows.
  3. `pipeline_runtime` selects units that do not yet have `page_to_card_job_id` and submits one `page-to-card` job per eligible unit to `job-queue-mcp`.
  4. `job-queue-mcp` delivers a notification when a `page-to-card` job has an accepted result or reaches a terminal non-accepted state.
  5. The source-pipeline webhook receiver authenticates the event, persists it idempotently, and wakes `pipeline_runtime`.
  6. `pipeline_runtime` processes the local event. For accepted result events, it rereads the accepted `result_payload["cards"]` result and creates missing initial `CardCandidate` rows by page result ordinal. For terminal non-accepted events, it records the affected job's terminal checkpoint and stops page-result fan-out plus repeated local polling for that job.
  7. `pipeline_runtime` submits one `card-review` job for each candidate that lacks `review_job_id`.
  8. `job-queue-mcp` delivers a notification when each `card-review` job has an accepted result or reaches a terminal non-accepted state.
  9. For accepted review results, `pipeline_runtime` rereads the result payload. When `passed=true`, `pipeline_handoff` posts the candidate title and content to `POST /api/v1/cards` with a stable `Idempotency-Key` and marks `ingestion_handoff_done=true` after `202 Accepted`.
  10. When `passed=false`, `pipeline_runtime` submits one `card-repair` job for the candidate when no repair job exists.
  11. `job-queue-mcp` delivers a notification when each `card-repair` job has an accepted result or reaches a terminal non-accepted state.
  12. For accepted repair results, `pipeline_runtime` rereads the result payload and creates child `CardCandidate` rows for each repaired card returned by `card-repair`.
  13. Child candidates re-enter the same review flow.
  14. `pipeline_runtime` periodically reconciles outstanding job linkages at a low frequency to catch missed notifications and terminal states.

## File Placement
- The source-processing app is owned by `apps/source_pipeline`.
- The accepted first-version layout is:
  - `apps/source_pipeline/alembic`
  - `apps/source_pipeline/src/source_pipeline/config.py`
  - `apps/source_pipeline/src/source_pipeline/db/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_intake/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_runtime/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_webhook/`
  - `apps/source_pipeline/src/source_pipeline/page_to_card/`
  - `apps/source_pipeline/src/source_pipeline/card_review/`
  - `apps/source_pipeline/src/source_pipeline/card_repair/`
  - `apps/source_pipeline/src/source_pipeline/pipeline_handoff/`
  - `apps/source_pipeline/src/source_pipeline/entrypoints/orchestrator.py`
  - `apps/source_pipeline/src/source_pipeline/entrypoints/webhook_receiver.py`
  - `apps/source_pipeline/tests/`
  - `infra/docker/source_pipeline/`
  - `infra/compose/docker-compose.base.yml` service entries for the dedicated `orchestrator` and source-pipeline webhook receiver processes

## Validation
- **Checks:**
  - Spec review confirms source intake, orchestration runtime, and step contracts are formal project-owned app boundaries rather than `human_workspace` scripts.
  - Contract tests verify `SourceUnit`, `CardDraft`, `CardReviewResult`, `CardRepairInput`, and `CardRepairResult` shapes.
  - Instruction tests verify page extraction, card review, and card repair share the same card-quality standard without duplicating transport-generic worker protocol instructions.
  - PostgreSQL-backed integration tests verify `workflow_runs`, `workflow_units`, and `card_candidates` are sufficient for restart/resume behavior without mirroring queue lifecycle state.
  - Webhook receiver tests verify `knowledge` Logto token validation, duplicate event handling, event persistence, and local wakeup behavior.
  - Queue integration tests verify accepted `page-to-card` notifications lead the runtime to reread results, create candidates, and fan out into one `card-review` job per candidate.
  - Runtime tests verify failed review results submit `card-repair` jobs and accepted repair results create zero or more child candidates that re-enter review.
  - Runtime tests verify `page-to-card`, `card-review`, and `card-repair` terminal non-accepted states stop automatic fan-out and do not create downstream candidates or handoffs.
  - Runtime tests verify `card-repair` accepted results with `cards=[]` stop the candidate lineage without creating child candidates.
  - Handoff tests verify passing review results call `POST /api/v1/cards`, mark completion only after `202 Accepted`, and retry failed handoff attempts with the same `Idempotency-Key`.
  - Idempotency tests verify repeated ticks do not duplicate review jobs, repair jobs, child candidates, or ingestion handoffs.
  - Integration tests verify knowledge ingestion deduplicates repeated accepted-card handoffs with the same `Idempotency-Key`, including timeout or connection-loss retries after the server accepted the original request.
- **Evidence:**
  - Approved spec review with synchronized updates to impacted design docs.
  - Passing PostgreSQL-backed state-transition tests for intake, webhook event intake, local event wakeup, candidate creation, repair loops, reread-from-queue behavior, low-frequency reconcile, ingestion handoff, and restart/resume behavior.
  - Passing contract tests for accepted `page-to-card`, `card-review`, and `card-repair` result shapes.
