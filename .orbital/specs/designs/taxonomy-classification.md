---
abstract: Job-queue-backed taxonomy classification orchestration for incrementally moving directly assigned cards through taxonomy child categories.
out_of_scope: Taxonomy tree persistence ownership, worker-side execution mechanics, and HTTP-triggered classification APIs.
---

# Design: taxonomy-classification

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy_classification` module that lets workers choose a direct child category for cards assigned to a selected taxonomy scope, moves valid child choices directly to that child category, persists continuation work after real assignment movement, and keeps cards assigned to the current scope when the worker chooses `Unclassified`.
- **Scope/Boundaries:** Covers operator-triggered seed job submission, one-card job contracts, local job linkage state, local continuation request state, queue-result notification intake, lightweight reconcile, result validation, assignment-move orchestration, and runtime continuation submission. Excludes taxonomy tree persistence ownership, worker-side implementation mechanics, and HTTP-triggered classification APIs.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth ownership stays in `knowledge_graph` and `taxonomy`, queue execution stays external to the API process, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** Classification execution is seeded by operator scripts and advanced by a background runtime. The runtime submits one `taxonomy_classification` queue job per eligible card through the job-queue producer batch-create surface, consumes notification-only webhook events plus lightweight polling/reconcile, reads result status through the job-queue batch result-read surface, validates target children against taxonomy-owned truth, moves assignments only through taxonomy-owned services, persists continuation requests after real assignment movement, and drains buffered continuation requests through the same job-queue producer batch boundary.
- **Update Rule:** Requirement-level constraints remain stable while classification orchestration behavior, queue contracts, result-consumption rules, and runtime/operator semantics are maintained here as implementation-facing truth.

## Design Approach
- **Approach:** Keep human taxonomy-structure control in operator scripts and delegate card-level classification judgment to `job-queue-mcp`. The local `taxonomy_classification` runtime owns queue interaction and result application. Workers return structured classification decisions only; they never write knowledge APIs or databases.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy_classification` owns classification job submission, job linkage persistence, continuation request persistence, result event processing, low-frequency reconcile, accepted-result validation, assignment-move orchestration, and continuation request draining.
  - **Dependency boundary:** `taxonomy_classification` consumes `knowledge_graph` service ports for card input data and consumes `taxonomy` service ports for scope lookup, child lookup, and assignment movement.
  - **Queue boundary:** Classification jobs are submitted to the `taxonomy_classification` queue in `job-queue-mcp`.
  - **Producer/result-reader SDK boundary:** `taxonomy_classification` uses the upstream `job_queue_mcp_client.producer.AsyncClient` and `job_queue_mcp_client.auth.ClientCredentialsTokenProvider` public facades directly for batch job submission, batch result reads, and machine-to-machine token acquisition. The module owns classification payload construction, output schema export, local linkage persistence, result validation, and assignment movement.
  - **Direct-assignment candidate rule:** Cards directly assigned to a taxonomy scope are classification candidates for that scope even when Graph View browsing does not expose those cards.
  - **Seed submission rule:** Operator scripts enqueue cards directly assigned to selected taxonomy scopes at run time. Runtime continuation only follows cards whose accepted classification result produced a real assignment move; it does not continuously scan all card assignments.
  - **Single-card job rule:** One knowledge card is processed by exactly one queue job for one scope classification attempt.
  - **Node context contract:** The worker receives only the selected card's `title` and `content`, the current scope breadcrumb path, and available sibling target category names.
  - **Human-structure rule:** The worker must choose among existing direct child category names of the current scope or choose `Unclassified` to keep the card in the current scope. The worker cannot create taxonomy nodes, request new taxonomy nodes, or move a card to the parent scope.
  - **Move target rule:** Choosing a child category moves the card assignment directly to that child category.
  - **Keep-current-scope rule:** Choosing `Unclassified` keeps the card assignment at the current scope and records the classification attempt as processed.
  - **Validation-before-move rule:** The runtime applies accepted results only after verifying that the card is still assigned to the source scope, the selected child still exists, and the selected child belongs directly to the source scope.
  - **Continuation trigger rule:** A valid accepted result creates continuation work only when assignment movement actually changes the card's taxonomy scope.
  - **Continuation policy boundary:** Continuation eligibility is evaluated from current taxonomy and assignment truth. The active policy submits another classification attempt for the moved card when the current target scope has direct child categories and the card has no active job for that target scope.
  - **Continuation stop rule:** Continuation stops when the result keeps the card in the current scope, the accepted result is invalid, the source assignment is stale, the queue job reaches a terminal non-accepted state, the current target scope has no direct child categories, the current assignment no longer matches the continuation request, or an active job already exists for the card and target scope.
  - **Continuation depth rule:** The continuation stop rule is the current stop boundary; the runtime does not maintain a separate fixed-depth counter.
  - **Invalid-result rule:** Invalid accepted results are recorded with an error and do not move assignments.
  - **No HTTP trigger surface:** First-version classification submission and taxonomy child creation are operator-script driven.
  - **Migration safety rule:** Schema changes that alter taxonomy assignment shape require zero active taxonomy-classification jobs before applying the change.

## Operator Script Contract
- **Create taxonomy children script:**
  - Input: one parent taxonomy node id and one or more child category names.
  - Behavior: calls taxonomy-owned services to create real child category nodes under the parent.
- **Submit classification jobs script:**
  - Input modes:
    - single-scope mode selected by case-insensitive `scope_name` or case-insensitive root-to-node `scope_path`;
    - all eligible scopes selected by `all_direct_assignments`.
  - `scope_name` matching rule: the name is matched case-insensitively across taxonomy nodes. A unique match selects that scope. No matches cause failure. Multiple matches fail and report each candidate breadcrumb so the operator can rerun with `scope_path`.
  - `scope_path` matching rule: each path segment is matched case-insensitively against the direct children of the prior segment, starting at the real root. A missing or ambiguous segment fails with the matching breadcrumb context.
  - `all_direct_assignments` scope rule: the script scans taxonomy nodes that have direct card assignments.
  - No-child skip rule: a scope with no direct child categories is skipped and counted as `skipped_no_children`.
  - Optional limit: limits the total number of submitted card jobs for the run after scope eligibility is resolved.
  - Batch sizing: limits each producer batch-create request to an item-count ceiling from 1 through 1000 and defaults to 1000. The service also automatically splits producer batch-create requests so each serialized request body stays below the 900 KiB producer body cap.
  - Selection set: cards currently assigned directly to each selected scope node and lacking an active outstanding classification job for the same scope assignment.
  - Ordering: scopes are processed by breadcrumb path and taxonomy node id; selected cards within a scope are processed in `nodes.id ASC`.
  - Submission preflight: the service aggregates pending local jobs, candidate cards, and already-linked active remote jobs for all selected scopes before submission. Scopes with no pending local jobs and no candidate cards keep their summary row but do not enter the per-scope submission path.
  - Local intent creation: the service creates and commits local active submission rows before producer batch submission so each row has a stable local job id.
  - Producer submission: one queue job per selected card is created through the producer batch-create SDK. Each request is bounded by both item count and serialized request-body size. Each batch item uses `taxonomy-classification-job:{local_job_id}` as its queue-scoped idempotency key.
  - Batch response handling: the service applies producer batch-create results by input index and writes the returned remote `job_id` to the matching local job row.
  - Idempotent recovery count: a batch result with `created=false` is counted as an idempotent remote job reuse for a previously created producer job.
  - Progress output: the script displays one aggregate progress indicator for jobs that require producer submission or producer-submission recovery. Already-linked jobs are excluded from progress.
  - Summary output: the default script output contains only selected-scope count, submitted-job count, idempotent-reuse count, already-linked-job count, skipped-no-child scope count, elapsed time, and effective submitted jobs per second.
  - Verbose output: per-scope details are available only through an explicit verbose mode.
  - Resubmission rule: a processed keep-current-scope result, processed invalid accepted result, or terminal non-accepted result does not block a later operator submission for the same card and scope.

## Queue Job Contract
- **Queue name:** `taxonomy_classification`.
- **Priority:** first-version default is `normal`.
- **Payload:** one JSON object containing:
  - `scope_path`: current root-to-scope breadcrumb path, formatted as names separated by ` / `, for example `Root / Science / Mathematics`
  - `card`: `{title, content}`
  - `children`: array of target category options for the scope, each item containing only `name`; it contains each direct child category plus one keep-current-scope `Unclassified` option.
- **Instruction:** task-specific guidance tells the worker only to classify the supplied card within the supplied taxonomy scope path into exactly one supplied direct child taxonomy category, or choose `Unclassified` when no child fits. Output formatting and case-insensitive name matching are enforced by the separate output schema and runtime validation, not repeated in the instruction text.
- **Output schema:** one JSON object containing:
  - `{ "target_name": <non-empty child name or Unclassified> }`
- **Result-use rule:** Publishing a valid move depends on structural validation against current taxonomy state. A `target_name` matches either a direct child of the scope or the keep-current-scope `Unclassified` option case-insensitively.
- **Producer idempotency rule:** The remote producer idempotency key is derived from the committed local classification job id. Re-running an interrupted operator submission reuses the same producer idempotency key for the same local active submission intent and receives the existing remote job id instead of creating a duplicate remote job.

## Runtime State
- The module persists local queue linkage and local notification state needed for restart/resume behavior.
- A classification job record stores:
  - scope node id
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
- A projection refresh request record stores:
  - affected `scope_kind`
  - affected `taxonomy_node_id`
  - optional last refresh error
  - timestamps
- A continuation request record stores:
  - target scope node id
  - card node id
  - source local classification job id
  - nullable next local classification job id
  - optional last submission error
  - timestamps
- Local state does not duplicate accepted result payloads, full queue lifecycle history, leases, or submission history from `job-queue-mcp`.

## Result Consumption
- The classification runtime uses the same result-consumption pattern as `source_pipeline`:
  - queue-level webhook subscriptions deliver notification-only events;
  - local webhook intake authenticates and persists events idempotently;
  - pending local events wake the background runtime;
  - accepted result payloads and not-ready status are reread through the configured job-queue batch result-read surface;
  - low-frequency polling/reconcile checks outstanding job links to compensate for missed notifications or exhausted remote delivery retries.
- The webhook receiver does not move assignments or read result payloads. It returns after authenticated atomic idempotent event persistence.
- The webhook receiver rejects authenticated notifications whose `queue_name` does not match the configured taxonomy-classification queue before writing any local event.
- The background runtime owns event processing, batch result reads, validation, assignment movement, continuation request creation, dirty projection request creation, terminal checkpoint updates, processed/error markers, buffered continuation submission, and bounded projection refresh work.
- Pending accepted-result webhook events are read in batches. Ready batch items are applied through existing per-job validation and assignment movement. Not-ready or not-found batch items for accepted-result webhook events are recorded as event processing errors because the webhook contract indicated an accepted result should be available.
- Low-frequency reconcile reads outstanding linked jobs in batches. Ready batch items are applied through existing per-job validation and assignment movement. Not-ready items whose remote state is a terminal non-accepted state mark the local job terminal; other not-ready items remain outstanding. Not-found items record a local job error while leaving the job outstanding for operator visibility.
- Local assignment movement remains per job and serial within a runtime tick so assignment locks and taxonomy validation keep existing conservative semantics while remote result I/O is batched.
- A real assignment move inserts a continuation request in the same transaction as accepted-result processing and projection refresh request creation. A keep-current-scope result does not insert a continuation request.
- Assignment movement records affected browse-visible taxonomy card-scope identities as projection refresh requests. Request insertion is idempotent by scope identity and happens in the same transaction as the accepted-result job/event processing state.
- Continuation submission is a local buffered follow-up step. The runtime checks pending continuation request count and oldest request age only after result event or reconcile work has been committed for the tick. It claims continuation requests when the pending count reaches the configured continuation request batch size or the oldest pending request reaches the configured continuation flush interval.
- Each claimed request validates that the card is still assigned to the request target scope, that the target scope has direct child categories, and that no active classification job already exists for the card and target scope. Eligible requests create or reuse a local classification job intent, and valid no-op stop conditions delete their continuation requests without remote submission.
- Continuation producer submission uses the same configured queue name, producer SDK boundary, producer item-count batch ceiling, request body limits, and `taxonomy-classification-job:{local_job_id}` idempotency rule as operator submission. Eligible continuation jobs are submitted through the shared producer batch-create path after local job intents are committed. Job Queue endpoints, credentials, and queue names remain runtime configuration, not module constants.
- Projection refresh is a derived read-model operation. The runtime processes pending result events before projection refresh work. When no result events are ready for a tick, the runtime claims a bounded set of dirty scope refresh requests, rebuilds each claimed scope projection, and deletes each request only after the refresh succeeds.
- Each projection refresh request is processed independently so one expensive or failing scope refresh does not roll back accepted-result job processing for unrelated events.
- Webhook receiver authentication remains module-owned and validates incoming delivery tokens against the `knowledge` Logto authority. The job-queue producer/result-reader SDK is not the authority for incoming webhook delivery-token validation.

## Assignment Move Flow
1. Operator creates direct child categories for one or more scope nodes.
2. Operator submits classification jobs for cards currently assigned directly to selected scope nodes.
3. `job-queue-mcp` dispatches each single-card job to external workers.
4. `job-queue-mcp` sends notification-only webhook events for accepted results and terminal non-accepted states.
5. The local webhook receiver records events idempotently and wakes the classification runtime.
6. The classification runtime reads accepted results and outstanding result status through batch result-read requests.
7. The runtime validates the accepted result against current taxonomy and assignment truth.
8. Valid child targets move the card directly to the target child through taxonomy-owned assignment movement and queue projection refresh requests for affected scopes.
9. Real assignment movement persists a continuation request for the moved card and target scope in the same transaction as accepted-result processing.
10. The runtime drains buffered continuation requests once the configured batch threshold is reached or the configured flush interval elapses, then submits eligible moved cards for their current target scopes when each target scope is still current, has direct child categories, and has no active classification job for that card and target scope.
11. Valid `unclassified` targets keep the card in the current source scope, mark the job processed, and do not create continuation work.
12. Invalid accepted results record a job processing error, mark the accepted result locally processed, remove the event wakeup, and leave the current assignment unchanged.
13. Terminal non-accepted states record terminal checkpoints and leave the current assignment unchanged.
14. Low-frequency reconcile repeats result and terminal checks for outstanding job links.
15. When result and continuation work are drained for a tick, the runtime refreshes queued scope projections and deletes only successfully refreshed requests.

## Runtime Configuration
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
  - pending event batch size;
  - continuation request batch size;
  - continuation flush interval;
  - projection refresh batch size.
- Settings boundary rule:
  - the taxonomy-classification runtime settings require job-queue producer/result-reader settings and do not require webhook auth settings.
  - the taxonomy-classification webhook receiver settings require queue name plus webhook auth/path settings and do not receive job-queue producer/result-reader client credentials.

## Failure Handling
- Job submission failures leave assignments unchanged and are visible in operator output or runtime logs.
- Producer batch-create failures leave local active submission rows with `job_id IS NULL`; a later operator run can resubmit those rows with the same producer idempotency keys and recover remote job ids without duplicate remote jobs.
- Accepted results with unknown child names or stale source assignments are recorded as locally processed errors and do not move assignments.
- Terminal non-accepted queue states are recorded to stop repeated local result reads for the affected job.
- Duplicate webhook deliveries are accepted idempotently through repository-owned atomic event insertion and do not create duplicate local wakeups.
- Duplicate operator submission runs do not submit another active job for the same card and scope when a linked outstanding job already exists. Processed and terminal job rows do not block later operator submissions.
- Runtime errors preserve enough local state for a later runtime tick to retry unprocessed events or reconcile outstanding jobs.
- Continuation producer submission failures preserve the affected continuation requests with `last_error` for later retry. If a local next-job intent has already been created, later retries reuse that local job id and the same remote idempotency key instead of creating duplicate active jobs.
- Continuation requests whose current assignment is stale, whose target scope has no direct child categories, or whose card already has an active job for the target scope are completed without remote submission.
- Projection refresh failures preserve the dirty scope request with `last_error` for a later retry and do not undo already-processed classification events.

## Validation
- **Checks:**
  - Operator child-creation script creates only requested child category nodes through taxonomy services.
  - Operator submission script resolves case-insensitive `scope_name` only when it uniquely identifies one taxonomy node.
  - Operator submission script reports candidate breadcrumbs and fails when case-insensitive `scope_name` matches multiple taxonomy nodes.
  - Operator submission script resolves case-insensitive `scope_path` segment by segment from the real root.
  - Operator submission script reports breadcrumb context and fails when a `scope_path` segment is missing or ambiguous.
  - Operator submission script scans eligible scope nodes when `all_direct_assignments` is selected.
  - Operator submission script skips scopes with no direct children and reports `skipped_no_children`.
  - Submission preflight tests verify selected scopes with no pending local jobs and no candidate cards do not enter the per-scope submission path.
  - Operator submission script selects cards directly assigned to each selected scope in `nodes.id ASC` order.
  - Submission idempotency tests verify repeated runs do not duplicate active job links for the same card and scope.
  - Producer batch submission tests verify local job ids drive stable producer idempotency keys, batch-create responses are applied by input index, idempotent remote reuses are counted, automatic request-body chunking keeps producer requests below the 900 KiB body cap, oversized single-job requests fail before remote submission, and interrupted submissions can be safely resumed.
  - Operator progress tests verify the default output contains one aggregate progress display and a compact summary without per-scope detail.
  - Operator verbose-output tests verify per-scope detail is emitted only in verbose mode.
  - Resubmission tests verify processed keep-current-scope results, processed invalid accepted results, and terminal non-accepted results do not block later submissions for cards still assigned to the same scope.
  - Queue-contract tests verify `taxonomy_classification` payload and output schema shape.
  - Webhook receiver tests verify authentication, duplicate event handling, event persistence, and local wakeup behavior.
  - Runtime tests verify accepted valid child targets move assignments directly to the target child.
  - Runtime tests verify accepted valid child targets that change assignment create continuation requests in the same local transaction as processed-job state and projection refresh requests.
  - Runtime tests verify accepted `unclassified` targets keep the current assignment and mark the job processed.
  - Runtime tests verify accepted `unclassified` targets do not create continuation requests.
  - Runtime tests verify unknown target names and stale source assignments record errors without moving assignments.
  - Runtime tests verify unknown target names, stale source assignments, and terminal non-accepted states do not create continuation requests.
  - Runtime tests verify terminal non-accepted queue states stop repeated processing for that job.
  - Runtime batch result-read tests verify accepted-result webhook events and low-frequency reconcile use the batch result-read SDK, preserve per-job validation semantics, and handle ready, not-ready, not-found, and terminal-state items correctly.
  - Reconcile tests verify outstanding job links are checked at low frequency through the batch result-read surface.
  - Continuation request tests verify moved cards are submitted for their current target scope only when the scope has direct child categories, no active job for that card and scope, and the card remains directly assigned to that scope.
  - Continuation request tests verify pending requests wait below the configured batch threshold until the configured flush interval elapses.
  - Continuation producer tests verify pending continuation requests reaching the configured batch threshold are submitted through the shared producer batch-create path.
  - Continuation request tests verify no-child, stale-assignment, and already-active-job requests are completed without remote submission.
  - Continuation producer tests verify continuation-created local jobs use the same configured queue name, batch-create producer client, request-size limits, and `taxonomy-classification-job:{local_job_id}` idempotency key semantics as operator-created jobs.
  - Continuation retry tests verify producer failures retain request state and retry through the same local next-job intent without duplicate active jobs.
  - Projection refresh request tests verify assignment moves enqueue source and target scopes once per scope, accepted-result job processing commits independently from projection refresh work, and refresh success removes only the refreshed scope request.
  - Projection refresh failure tests verify failed scope refreshes retain retry state without re-opening processed result events.
- **Evidence:**
  - Passing unit and integration tests for operator scripts, queue contracts, webhook intake, result processing, assignment movement, and reconcile behavior.
