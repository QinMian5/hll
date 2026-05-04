---
abstract: Recoverable external import design for loading preprocessed Wikipedia article shards into the isolated knowledge corpus database.
out_of_scope: Online API integration, knowledge corpus schema design, processed-document marking workflows, and LLM-driven document selection.
---

# Design: wikipedia-corpus-import

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted design for an external Wikipedia import orchestrator that streams canonical article shards from preprocessing outputs into `wikipedia.documents` inside the isolated knowledge corpus database.
- **Scope/Boundaries:** Covers script placement, streaming shard traversal, recoverable per-shard state markers, shard-level concurrency, batch upsert behavior, and import-progress observability. Excludes knowledge corpus internal schema ownership, keyword search behavior, processed-document marking, and direct runtime coupling to online apps.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Offline data-preparation workflows must remain outside online runtime ownership, repository boundaries must stay explicit, and behavior-changing orchestration changes must keep active specs current.
- **Detail Commitments:** The repository owns a recoverable external import entrypoint at `apps/operator_tools/src/knowledge_operator/knowledge_corpus/import_wikipedia_shards.py` that reads `articles/**/*.jsonl.zst`, uses the `apps/knowledge_corpus` library boundary for batched record upsert, and tracks progress through per-shard marker files rather than database import state.
- **Update Rule:** Requirement-level governance stays stable while this design owns importer placement, checkpoint semantics, concurrency policy, and observability details.

## Inputs & Outputs
- **Inputs:**
  - A root directory containing preprocessed canonical article shards under `articles/**/*.jsonl.zst`.
  - A separate state directory for recoverable shard marker files, logs, and aggregate progress stats.
  - Knowledge corpus runtime configuration via current process environment, including `KNOWLEDGE_CORPUS_DATABASE_URL`.
  - Import configuration such as worker count, batch size, and optional shard limits.
- **Outputs:**
  - Upserted rows in `wikipedia.documents`.
  - Per-shard marker files expressing `running`, `completed`, or `failed` state.
  - Aggregate progress and event logs under the import state directory.
  - Terminal progress output for total shard progress and active worker status.

## Design Approach
- **Approach:** Implement a recoverable import orchestrator in `apps/operator_tools/src/knowledge_operator/knowledge_corpus/import_wikipedia_shards.py`. The entrypoint remains external to `apps/knowledge_corpus`, streams preprocessed article shards, and coordinates shard-level worker processes that batch-write records through the existing knowledge corpus library.
- **Key Elements:**
  - **External orchestration boundary:** The importer lives under `apps/operator_tools` and is not part of the `knowledge_corpus` app package. It may import `knowledge_corpus` library modules but does not move file traversal or checkpoint state into the app.
  - **Input contract:** The importer consumes canonical article shards only. It does not read redirect-alias or disambiguation outputs.
  - **Checkpoint location:** The importer writes recoverable state to a caller-supplied state root separate from the article source tree.
  - **Single-run lock:** The importer acquires an exclusive lock file under the state root before dispatching workers. A concurrent run against the same state root fails fast.
  - **Per-shard marker strategy:** Shard progress is tracked with individual marker files instead of database rows. Marker files are the source of truth for resume behavior.
  - **Shard states:** Accepted states are `pending` (no marker file), `running`, `completed`, and `failed`.
  - **Marker payload:** Each shard marker carries `shard_id`, `input_path`, `status`, and `worker_id`. Aggregate progress stats plus event/failure logs carry run-level counts and error details.
  - **Shard claiming rule:** A worker claims a shard by atomically creating the shard's `running` marker. Only the worker that successfully creates the marker owns the shard.
  - **Resume rule:** The importer skips `completed` shards, retries `failed` shards, and may reclaim stale `running` shards from prior interrupted runs because document upsert is already idempotent by `page_id`.
  - **Concurrency model:** The importer uses one coordinator process plus multiple worker processes. Each worker processes one shard at a time and uses the current knowledge corpus database runtime for batched writes inside the worker process.
  - **Batch write rule:** Workers accumulate records into bounded batches before calling the knowledge corpus upsert service. The accepted first-version default is `batch_size=1000`, with caller override allowed.
  - **Default concurrency:** The accepted first-version default is `workers=3`. The importer may allow caller override, but first-version tuning is intentionally conservative because the workload combines external-disk reads, zstd decompression, JSON parsing, PostgreSQL upsert, and `search_vector` generation.
  - **Database idempotency dependency:** The importer relies on `wikipedia.documents.page_id` primary-key uniqueness plus `ON CONFLICT DO UPDATE` semantics to guarantee that replaying a shard does not create duplicate document rows.
  - **Failure handling:** If a batch write fails, the owning worker marks the entire shard `failed`, records the error, and stops that shard. Other shards continue running.
  - **Interrupt handling:** On `Ctrl+C`, the coordinator records an `import-interrupted` event and forcefully tears down all worker processes using a terminate-then-kill fallback across the full executor lifecycle (including claim/dispatch and result-collection stages) so the import does not leave long-lived child processes behind. Shards already marked `completed` stay complete; shards still in `running` state remain resumable and are reclaimed on the next run.
  - **Observability artifacts:** The state root includes per-shard marker files plus aggregate progress stats and append-only event/failure logs so long-running imports remain inspectable without reading database state.
  - **Terminal progress contract:** When terminal progress is enabled, the importer uses a Rich total-progress display rather than per-shard line printing. The accepted first-version display shows total shard progress, total document progress, docs-per-second throughput, elapsed time, and ETA, while worker-specific detail stays out of the terminal surface.
  - **No processed-document writes:** The importer only loads `wikipedia.documents`. It does not create `wikipedia.processed_documents` rows.
- **Interactions:**
  1. The coordinator discovers all article shards beneath the supplied `articles_root`.
  2. The coordinator enumerates shard state from marker files beneath `state_root`.
  3. Workers claim unowned shards by atomically creating `running` markers.
  4. Each worker streams one shard, parses JSONL records, batches them, and calls the `knowledge_corpus` upsert interface inside worker-local database sessions.
  5. On success the worker replaces the shard marker with `completed`; on failure it replaces the marker with `failed` and records error details.
  6. Aggregate stats and event logs are updated so operators or follow-on programs can observe progress and resume safely.

## Validation
- **Checks:**
  - Spec review confirms the importer remains outside `apps/knowledge_corpus` while using the app's record-level library interface.
  - Import tests verify shard discovery, marker-state transitions, resume behavior, and failure handling.
  - Concurrency tests verify multiple workers do not double-claim the same shard.
  - Integration tests verify batched imports populate `wikipedia.documents` without duplicate rows after replay.
  - Progress/logging checks verify the importer emits aggregate stats and event logs under the state root.
- **Evidence:**
  - Approved spec review with synchronized updates to impacted design docs.
  - Passing importer tests for marker semantics and replay behavior.
  - Passing integration tests demonstrating idempotent replay into the knowledge corpus database.
