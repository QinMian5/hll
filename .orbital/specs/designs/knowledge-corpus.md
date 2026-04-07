---
abstract: Local-only knowledge corpus app design for isolated source-document persistence, PostgreSQL keyword retrieval, and processed-document bookkeeping.
out_of_scope: HTTP APIs, operator-facing CLI commands, file-system import orchestration, embedding/vector retrieval, and automatic synchronization into the online knowledge graph.
---

# Design: knowledge-corpus

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted design for a repository-local but runtime-isolated knowledge corpus app that stores external source documents for personal/offline workflows, supports PostgreSQL keyword retrieval, and records which documents have already been processed into another system.
- **Scope/Boundaries:** Covers the app boundary, isolated PostgreSQL ownership, source-specific schema strategy, Python-library interfaces, Wikipedia-first schema commitments, processed/unprocessed filtering, and architecture isolation rules. Excludes online API/runtime integration, operator-facing CLI contracts, file/directory traversal orchestration for ingestion, vector search, and cross-source federation.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository module boundaries remain explicit, offline/personal tooling must not pollute online runtime ownership, environment behavior must stay reproducible, and active specs must capture only current accepted truth.
- **Detail Commitments:** The repository adds `apps/knowledge_corpus` as a fully independent Python app with its own dependencies, settings, Alembic migrations, SQLAlchemy metadata, and a dedicated PostgreSQL service managed through repository infrastructure assets. First-version persistence uses a `wikipedia` schema inside the dedicated database and exposes only Python-library interfaces for record upsert, keyword search, processed filtering, and processed marking.
- **Update Rule:** Requirement-level governance stays stable while this design owns app-specific file paths, schema contracts, retrieval semantics, and isolation rules.

## Inputs & Outputs
- **Inputs:**
  - Record-level document write requests from external scripts/programs.
  - Keyword-search requests with filtering options such as `exclude_processed`.
  - Processed-document mark requests keyed by source document identifier.
  - Dedicated app configuration, including the connection string for the isolated PostgreSQL service.
- **Outputs:**
  - Persisted source documents in PostgreSQL.
  - Search results ranked by PostgreSQL full-text search.
  - Processed-document bookkeeping rows that allow later exclusion from search/listing.
  - Python return values and exceptions only; no HTTP or CLI output contracts.
- **Artifacts:**
  - One repository app at `apps/knowledge_corpus`.
  - One isolated PostgreSQL service owned by the app and provisioned through repository-managed Docker/env/migration assets.
  - Source-specific schemas, with `wikipedia` defined first.
  - Source-document and processed-document tables.

## Design Approach
- **Approach:** Build `apps/knowledge_corpus` as an independent local app that owns a dedicated PostgreSQL service and exposes only importable Python-library services. The app stores source documents for later human/AI-driven processing, provides PostgreSQL full-text keyword retrieval, and tracks processed documents in a separate table so source-document truth remains single-purpose.
- **Key Elements:**
  - **Independent app boundary:** `apps/knowledge_corpus` is not part of the online API runtime and is not a shared package. It owns its own `pyproject.toml`, settings/config, Alembic migrations, SQLAlchemy metadata, tests, and database lifecycle.
  - **Hard isolation rule:** `apps/knowledge_corpus` must not import `apps/api`, `apps/cli`, `apps/web`, or any other repository app. Existing apps must not import `apps/knowledge_corpus`.
  - **Dedicated PostgreSQL service:** The app uses a separate PostgreSQL service rather than sharing the online graph database. The service exists only for local/offline corpus usage.
  - **Repository-managed service lifecycle:** The dedicated PostgreSQL service is part of repository-managed infrastructure, environment files, and migration flow while remaining isolated from the online API/worker database lifecycle. The accepted first-version infra contract uses a dedicated database service and a dedicated one-shot migration service for knowledge corpus.
  - **Source-specific schema strategy:** Each external source gets its own schema inside the dedicated corpus database. The accepted first-version schema is `wikipedia`. Future sources may add more schemas without changing the first-version `wikipedia` contract.
  - **Wikipedia tables:** First version defines exactly two tables under `wikipedia`:
    - `wikipedia.documents`
    - `wikipedia.processed_documents`
  - **`wikipedia.documents` contract:** Holds source-document truth only. Required fields are:
    - `page_id`
    - `url`
    - `title`
    - `clean_text`
    - `search_vector`
    - `title` uses PostgreSQL `TEXT`, matching the repository convention already used for primary title-bearing knowledge records.
  - **`wikipedia.processed_documents` contract:** Holds processing-state truth only. Required fields are:
    - `page_id`
    - `processed_at`
    - `external_target_ref`
  - **Processed-state separation:** `processed_documents` must not duplicate `url`, `title`, or `clean_text`. The source-document table remains the only source of text truth.
  - **Python-library-only interface:** First version exposes only importable Python services. It does not expose HTTP routes or operator CLI commands.
  - **App-local configuration contract:** The app owns its own database runtime and migration URL settings and must not reuse the online API/worker database settings or config loaders. Accepted first-version setting names are `KNOWLEDGE_CORPUS_DATABASE_URL` and `KNOWLEDGE_CORPUS_MIGRATION_DATABASE_URL`.
  - **Async database runtime:** The app uses async SQLAlchemy engine and session boundaries for its database runtime and library services.
  - **Environment-loading rule:** The app, its tests, and its Alembic environment read only current process environment through `pydantic-settings`. Local `.env` files, compose `env_file`, and repository-root discovery are outside the app boundary and remain caller concerns.
- **Record-level interface boundary:** The app accepts record-level write/search/mark operations, not file-path or directory-path orchestration commands. External scripts or other local programs are responsible for reading Wikipedia preprocessing outputs and calling the library with normalized records.
- **External importer separation:** Recoverable Wikipedia shard import orchestration is defined outside this app boundary and is documented in `wikipedia-corpus-import`.
- **External page-to-card separation:** LLM-assisted page-to-card extraction orchestration remains outside this app boundary and may consume complete page records plus the processed-mark library interface without moving agent/session logic into `apps/knowledge_corpus`.
  - **Search semantics:** Retrieval uses PostgreSQL full-text search with the English configuration. Search must weight `title` above `clean_text` and support filtering out rows that already appear in `wikipedia.processed_documents`.
  - **Write semantics:** Source-document writes are idempotent by `page_id`. Processed-document marking is also idempotent by `page_id`.
  - **Replay-write minimization:** Document upsert updates existing rows only when source fields actually change, so replaying identical shards avoids unnecessary heap/index churn.
  - **No source-coupled importer contract:** The app does not define `import-wikipedia-from-path` or any directory-scanning/file-parsing API. Source-file orchestration remains outside the app boundary.
- **Interactions:**
  1. An external script/program reads normalized source records from an upstream workflow such as Wikipedia preprocessing.
  2. That caller invokes the `knowledge_corpus` library to upsert one or more document records into `wikipedia.documents`.
  3. A caller issues a keyword query through the library, optionally requesting `exclude_processed=true`.
  4. The search layer queries `wikipedia.documents`, applies PostgreSQL ranking and `processed_documents` exclusion, and returns document records.
  5. After the caller finishes handling a document, it records completion by calling the processed-marking interface, which upserts into `wikipedia.processed_documents`.
  6. Future searches can exclude already processed documents without mutating source-document truth.

## Validation
- **Checks:**
  - Spec review confirms the design keeps `knowledge_corpus` completely isolated from online API/CLI/runtime ownership.
  - Repository-structure and module-boundary docs are updated so the new app placement and non-import rules remain canonical.
  - Schema/model tests verify `wikipedia.documents` and `wikipedia.processed_documents` expose exactly the accepted first-version fields and constraints.
  - Repository tests verify document upsert idempotency, processed-mark idempotency, and unprocessed filtering behavior.
  - Search tests verify title-weighted full-text retrieval and `exclude_processed` filtering.
  - Repository quality-gate scripts and pre-commit hooks include `apps/knowledge_corpus` so the app stays under the standard Ruff, Ty, and pytest checks used in the repository.
- **Evidence:**
  - Approved spec review with synchronized updates to impacted design docs.
  - Passing migration/schema tests for the dedicated corpus database.
  - Passing repository/search tests demonstrating keyword retrieval and processed exclusion.
  - Passing repository quality gates and knowledge-corpus pre-commit hooks.
