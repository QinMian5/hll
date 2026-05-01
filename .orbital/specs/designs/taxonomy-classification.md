---
abstract: Job-queue-backed taxonomy classification orchestration for incrementally moving cards out of visible Unclassified leaves.
out_of_scope: Taxonomy tree persistence ownership, worker-side execution mechanics, and HTTP-triggered classification APIs.
---

# Design: taxonomy-classification

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy_classification` module that lets workers choose a regular direct child for cards in selected `Unclassified` leaves, then moves valid child choices to that child's `Unclassified` leaf or keeps the current `Unclassified` leaf.
- **Scope/Boundaries:** Covers operator-triggered one-shot job submission, one-card job contracts, local job linkage state, queue-result notification intake, lightweight reconcile, result validation, and assignment-move orchestration. Excludes taxonomy tree persistence ownership, worker-side implementation mechanics, and HTTP-triggered classification APIs.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth ownership stays in `knowledge_graph` and `taxonomy`, queue execution stays external to the API process, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** Classification execution is operator-triggered via one-shot scripts and advanced by a background runtime. The runtime submits one `taxonomy_classification` queue job per eligible card through the job-queue producer batch-create surface, consumes notification-only webhook events plus lightweight polling/reconcile, reads result status through the job-queue batch result-read surface, validates target children against taxonomy-owned truth, and moves assignments only through taxonomy-owned services.
- **Update Rule:** Requirement-level constraints remain stable while classification orchestration behavior, queue contracts, result-consumption rules, and runtime/operator semantics are maintained here as implementation-facing truth.

## Design Approach
- **Approach:** Keep human taxonomy-structure control in operator scripts and delegate card-level classification judgment to `job-queue-mcp`. The local `taxonomy_classification` runtime owns queue interaction and result application. Workers return structured classification decisions only; they never write knowledge APIs or databases.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy_classification` owns classification job submission, job linkage persistence, result event processing, low-frequency reconcile, accepted-result validation, and assignment-move orchestration.
  - **Dependency boundary:** `taxonomy_classification` consumes `knowledge_graph` service ports for card input data and consumes `taxonomy` service ports for scope lookup, child lookup, and assignment movement.
  - **Queue boundary:** Classification jobs are submitted to the `taxonomy_classification` queue in `job-queue-mcp`.
  - **Producer/result-reader SDK boundary:** `taxonomy_classification` uses the upstream `job_queue_mcp_client.producer.AsyncClient` and `job_queue_mcp_client.auth.ClientCredentialsTokenProvider` public facades directly for batch job submission, batch result reads, and machine-to-machine token acquisition. The module owns classification payload construction, output schema export, local linkage persistence, result validation, and assignment movement.
  - **One-shot submission rule:** Operator scripts enqueue the cards that are currently unclassified at run time. The module does not run a continuous service that automatically submits every future `Unclassified` card.
  - **Single-card job rule:** One knowledge card is processed by exactly one queue job for one scope classification attempt.
  - **Node context contract:** The worker receives only the selected card's `title` and `content`, the current scope breadcrumb path, and available sibling target category names.
  - **Human-structure rule:** The worker must choose among existing human-created direct child category names of the current scope or keep the card in the current scope's `Unclassified` leaf. The worker cannot create taxonomy nodes, request new taxonomy nodes, or move a card to the parent scope.
  - **Move target rule:** Choosing a child category moves the card assignment to that child category's `Unclassified` leaf.
  - **Keep-unclassified rule:** Choosing `Unclassified` keeps the card assignment at the current scope's `Unclassified` leaf and records the classification attempt as processed.
  - **Validation-before-move rule:** The runtime applies accepted results only after verifying that the card is still assigned to the source `Unclassified` leaf, the selected child still exists, the selected child belongs directly to the scope node, and the selected child's `Unclassified` leaf exists.
  - **Invalid-result rule:** Invalid accepted results are recorded with an error and do not move assignments.
  - **No HTTP trigger surface:** First-version classification submission and taxonomy child creation are operator-script driven.

## Operator Script Contract
- **Create taxonomy children script:**
  - Input: one parent taxonomy node id and one or more child category names.
  - Behavior: calls taxonomy-owned services to create regular child category nodes under the parent.
  - Side effect: each regular child category receives its own system-created `Unclassified` child leaf.
- **Submit classification jobs script:**
  - Input modes:
    - single-scope mode selected by case-insensitive `scope_name` or case-insensitive root-to-node `scope_path`;
    - all eligible scopes selected by `all_unclassified`.
  - `scope_name` matching rule: the name is matched case-insensitively across regular taxonomy nodes. A unique match selects that scope. No matches cause failure. Multiple matches fail and report each candidate breadcrumb so the operator can rerun with `scope_path`.
  - `scope_path` matching rule: each path segment is matched case-insensitively against the direct children of the prior segment, starting at the real root. A missing or ambiguous segment fails with the matching breadcrumb context.
  - `all_unclassified` scope rule: the script scans all regular taxonomy nodes that have a direct `Unclassified` leaf.
  - No-child skip rule: a scope with no regular direct child categories is skipped and counted as `skipped_no_children`.
  - Optional limit: limits the total number of submitted card jobs for the run after scope eligibility is resolved.
  - Batch size: limits each producer batch-create request to a value from 1 through 1000 and defaults to 1000.
  - Selection set: cards currently assigned to each selected scope node's direct `Unclassified` leaf and lacking an active outstanding classification job for the same scope and source assignment.
  - Ordering: scopes are processed by breadcrumb path and taxonomy node id; selected cards within a scope are processed in `nodes.id ASC`.
  - Local intent creation: the service creates and commits local active submission rows before producer batch submission so each row has a stable local job id.
  - Producer submission: one queue job per selected card is created through the producer batch-create SDK. Each batch item uses `taxonomy-classification-job:{local_job_id}` as its queue-scoped idempotency key.
  - Batch response handling: the service applies producer batch-create results by input index and writes the returned remote `job_id` to the matching local job row.
  - Idempotent recovery count: a batch result with `created=false` is counted as an idempotent remote job reuse for a previously created producer job.
  - Progress output: the script displays one aggregate progress indicator for jobs that require producer submission or producer-submission recovery. Already-linked jobs are excluded from progress.
  - Summary output: the default script output contains only selected-scope count, submitted-job count, idempotent-reuse count, already-linked-job count, skipped-no-child scope count, elapsed time, and effective submitted jobs per second.
  - Verbose output: per-scope details are available only through an explicit verbose mode.
  - Resubmission rule: a processed keep-unclassified result, processed invalid accepted result, or terminal non-accepted result does not block a later operator submission for the same card and scope.

## Queue Job Contract
- **Queue name:** `taxonomy_classification`.
- **Priority:** first-version default is `normal`.
- **Payload:** one JSON object containing:
  - `scope_path`: current root-to-scope breadcrumb path, formatted as names separated by ` / `, for example `Root / Science / Mathematics`
  - `card`: `{title, content}`
  - `children`: array of target category options for the scope, each item containing only `name`; it contains each direct regular child category plus the scope's direct `Unclassified` leaf.
- **Instruction:** task-specific guidance tells the worker only to classify the supplied card within the supplied taxonomy scope path into exactly one supplied direct child taxonomy category, or keep it in `Unclassified` when no child fits. Output formatting and case-insensitive name matching are enforced by the separate output schema and runtime validation, not repeated in the instruction text.
- **Output schema:** one JSON object containing:
  - `{ "target_name": <non-empty child name or Unclassified> }`
- **Result-use rule:** Publishing a valid move depends on structural validation against current taxonomy state. A `target_name` matches either a direct regular child of the scope or the scope's `Unclassified` leaf case-insensitively.
- **Producer idempotency rule:** The remote producer idempotency key is derived from the committed local classification job id. Re-running an interrupted operator submission reuses the same producer idempotency key for the same local active submission intent and receives the existing remote job id instead of creating a duplicate remote job.

## Runtime State
- The module persists local queue linkage and local notification state needed for restart/resume behavior.
- A classification job record stores:
  - scope node id
  - source `Unclassified` leaf id
  - card node id
  - nullable remote `job_id`, assigned only after the local active submission intent is committed and the producer batch-create response is applied
  - terminal non-accepted state when present
  - accepted-result processing state
  - result target snapshot when accepted and valid
  - last error when processing fails
  - timestamps
- Active job linkage is defined by local job rows with `processed_at IS NULL` and `terminal_state IS NULL`.
- A webhook event record stores:
  - stable event id
  - event type
  - remote job id
  - queue name
  - submission id or terminal state
  - processed timestamp
  - last error
- Local state does not duplicate accepted result payloads, full queue lifecycle history, leases, or submission history from `job-queue-mcp`.

## Result Consumption
- The classification runtime uses the same result-consumption pattern as `source_pipeline`:
  - queue-level webhook subscriptions deliver notification-only events;
  - local webhook intake authenticates and persists events idempotently;
  - pending local events wake the background runtime;
  - accepted result payloads and not-ready status are reread through `POST /results/batch`;
  - low-frequency polling/reconcile checks outstanding job links to compensate for missed notifications or exhausted remote delivery retries.
- The webhook receiver does not move assignments or read result payloads. It returns after authenticated atomic idempotent event persistence.
- The webhook receiver rejects authenticated notifications whose `queue_name` does not match the configured taxonomy-classification queue before writing any local event.
- The background runtime owns event processing, batch result reads, validation, assignment movement, terminal checkpoint updates, and processed/error markers.
- Pending accepted-result webhook events are read in batches. Ready batch items are applied through existing per-job validation and assignment movement. Not-ready or not-found batch items for accepted-result webhook events are recorded as event processing errors because the webhook contract indicated an accepted result should be available.
- Low-frequency reconcile reads outstanding linked jobs in batches. Ready batch items are applied through existing per-job validation and assignment movement. Not-ready items whose remote state is a terminal non-accepted state mark the local job terminal; other not-ready items remain outstanding. Not-found items record a local job error while leaving the job outstanding for operator visibility.
- Local assignment movement remains per job and serial within a runtime tick so assignment locks, taxonomy validation, and projection refreshes keep existing conservative semantics while remote result I/O is batched.
- Webhook receiver authentication remains module-owned and validates incoming delivery tokens against the `knowledge` Logto authority. The job-queue producer/result-reader SDK is not the authority for incoming webhook delivery-token validation.

## Assignment Move Flow
1. Operator creates direct child categories for one or more scope nodes.
2. Taxonomy service creates each requested child category plus that child's `Unclassified` leaf.
3. Operator submits classification jobs for cards currently assigned to selected scope `Unclassified` leaves.
4. `job-queue-mcp` dispatches each single-card job to external workers.
5. `job-queue-mcp` sends notification-only webhook events for accepted results and terminal non-accepted states.
6. The local webhook receiver records events idempotently and wakes the classification runtime.
7. The classification runtime reads accepted results and outstanding result status through batch result-read requests.
8. The runtime validates the accepted result against current taxonomy and assignment truth.
9. Valid child targets move the card to the target child's `Unclassified` leaf through taxonomy-owned assignment movement.
10. Valid `unclassified` targets keep the card in the current source `Unclassified` leaf and mark the job processed.
11. Invalid accepted results record a job processing error, mark the accepted result locally processed, remove the event wakeup, and leave the current assignment unchanged.
12. Terminal non-accepted states record terminal checkpoints and leave the current assignment unchanged.
13. Low-frequency reconcile repeats result and terminal checks for outstanding job links.

## Runtime Configuration
- Classification runtime configuration is independent from `apps/cli` reviewer configuration.
- API shared settings remain free of taxonomy-classification producer/result-reader and webhook receiver secrets.
- Taxonomy-classification runtime and webhook receiver settings use dedicated settings classes sourced from process environment.
- Classification settings include:
  - runtime-only job-queue base URL;
  - runtime-only job-queue token URL;
  - runtime-only job-queue client id;
  - runtime-only job-queue client secret;
  - runtime-only job-queue resource/audience;
  - runtime-only job-queue scopes for job creation and result reads;
  - receiver-only webhook authentication issuer/resource/discovery URL;
  - receiver-only webhook allowed caller client id;
  - receiver-only webhook public path;
  - runtime poll interval;
  - runtime reconcile interval;
  - pending event batch size.
- Settings boundary rule:
  - the taxonomy-classification runtime settings require job-queue producer/result-reader settings and do not require webhook auth settings.
  - the taxonomy-classification webhook receiver settings require queue name plus webhook auth/path settings and do not receive job-queue producer/result-reader client credentials.

## Failure Handling
- Job submission failures leave assignments unchanged and are visible in operator output or runtime logs.
- Producer batch-create failures leave local active submission rows with `job_id IS NULL`; a later operator run can resubmit those rows with the same producer idempotency keys and recover remote job ids without duplicate remote jobs.
- Accepted results with unknown child names, missing target `Unclassified` leaves, or stale card-source assignments are recorded as locally processed errors and do not move assignments.
- Terminal non-accepted queue states are recorded to stop repeated local result reads for the affected job.
- Duplicate webhook deliveries are accepted idempotently through repository-owned atomic event insertion and do not create duplicate local wakeups.
- Duplicate operator submission runs do not submit another active job for the same card and scope when a linked outstanding job already exists. Processed and terminal job rows do not block later operator submissions.
- Runtime errors preserve enough local state for a later runtime tick to retry unprocessed events or reconcile outstanding jobs.

## Validation
- **Checks:**
  - Operator child-creation script creates children through taxonomy services and automatically creates each child's `Unclassified` leaf.
  - Operator submission script resolves case-insensitive `scope_name` only when it uniquely identifies one regular taxonomy node.
  - Operator submission script reports candidate breadcrumbs and fails when case-insensitive `scope_name` matches multiple regular taxonomy nodes.
  - Operator submission script resolves case-insensitive `scope_path` segment by segment from the real root.
  - Operator submission script reports breadcrumb context and fails when a `scope_path` segment is missing or ambiguous.
  - Operator submission script scans all eligible scope `Unclassified` leaves when `all_unclassified` is selected.
  - Operator submission script skips scopes with no regular direct children and reports `skipped_no_children`.
  - Operator submission script selects cards from each selected scope's `Unclassified` leaf in `nodes.id ASC` order.
  - Submission idempotency tests verify repeated runs do not duplicate active job links for the same card and scope.
  - Producer batch submission tests verify local job ids drive stable producer idempotency keys, batch-create responses are applied by input index, idempotent remote reuses are counted, and interrupted submissions can be safely resumed.
  - Operator progress tests verify the default output contains one aggregate progress display and a compact summary without per-scope detail.
  - Operator verbose-output tests verify per-scope detail is emitted only in verbose mode.
  - Resubmission tests verify processed keep-unclassified results, processed invalid accepted results, and terminal non-accepted results do not block later submissions for cards still assigned to the same scope `Unclassified` leaf.
  - Queue-contract tests verify `taxonomy_classification` payload and output schema shape.
  - Webhook receiver tests verify authentication, duplicate event handling, event persistence, and local wakeup behavior.
  - Runtime tests verify accepted valid child targets move assignments to the target child's `Unclassified` leaf.
  - Runtime tests verify accepted `unclassified` targets keep the current assignment and mark the job processed.
  - Runtime tests verify unknown target names, stale source assignments, and missing target `Unclassified` leaves record errors without moving assignments.
  - Runtime tests verify terminal non-accepted queue states stop repeated processing for that job.
  - Runtime batch result-read tests verify accepted-result webhook events and low-frequency reconcile use the batch result-read SDK, preserve per-job validation semantics, and handle ready, not-ready, not-found, and terminal-state items correctly.
  - Reconcile tests verify outstanding job links are checked at low frequency through the batch result-read surface.
- **Evidence:**
  - Passing unit and integration tests for operator scripts, queue contracts, webhook intake, result processing, assignment movement, and reconcile behavior.
