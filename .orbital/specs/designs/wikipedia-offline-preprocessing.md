---
abstract: Offline preprocessing design for turning Wikipedia multistream dump splits into reproducible canonical article, redirect alias, and disambiguation JSONL datasets.
out_of_scope: Direct ingestion into online API/runtime paths, full MediaWiki template rendering fidelity, and downstream retrieval/indexing policy.
---

# Design: wikipedia-offline-preprocessing

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted offline preprocessing pipeline for Wikipedia multistream dumps so the repository can produce a stable, resumable, and auditable source dataset for later knowledge-ingestion work.
- **Scope/Boundaries:** Covers dump split discovery, split-local processing, XML page extraction, page classification, clean-text normalization, deterministic shard writing, manifests/stats/logging, and resume semantics. Excludes direct database writes, online API integration, existing CLI review behavior, and downstream indexing or retrieval policy.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository governance remains unified, module boundaries stay explicit even under a script-first implementation constraint, runtime behavior remains reproducible, and accepted behavior lives only in current active specs.
- **Detail Commitments:** First-version preprocessing lives under `human_workspace/` as a script-first pipeline with clear internal boundaries. The pipeline consumes Wikipedia multistream XML `.bz2` split files and writes split-aligned compressed JSONL datasets plus manifests, stats, and logs. XML parsing uses streaming semantics; full XML dump extraction to disk is not part of the accepted path.
- **Update Rule:** Requirement-level governance remains stable while this document holds preprocessing-specific file layout, record schemas, parsing behavior, failure semantics, and validation rules.

## Inputs & Outputs
- **Inputs:**
  - Wikipedia multistream XML split files matching `pages-articles-multistream*.xml-*.bz2`.
  - Run configuration for input root, output root, shard rolling policy, and failure thresholds.
  - Script version and cleaning configuration captured into the run manifest.
- **Outputs:**
  - `articles/split-<id>/shard-<id>.jsonl.zst`
  - `redirect_aliases/split-<id>/shard-<id>.jsonl.zst`
  - `disambiguation/split-<id>/shard-<id>.jsonl.zst`
  - `manifests/*.json`
  - `stats/*.json`
  - `logs/*.jsonl`
- **Artifacts:**
  - Canonical article records with clean human-readable text.
  - Redirect alias records for later title normalization and recall support.
  - Disambiguation metadata records for later retrieval assistance.
  - Run-level and split-level manifests, counters, and failure diagnostics.

## Design Approach
- **Approach:** Use a split-aligned offline preprocessing pipeline whose main path is `bz2 stream -> XML page extraction -> page classification -> canonical cleaning -> deterministic shard writing`. The implementation remains script-first under `human_workspace/`, but its responsibilities are separated so it can later move into a formal app boundary without redesigning the data contracts.
- **Key Elements:**
  - **Script boundary:** The accepted script set is one controller entrypoint plus focused helper modules for XML extraction, content cleaning, artifact writing, and typed record/runtime models.
  - **Input discovery:** The pipeline scans only XML split dump files, orders them deterministically by dump filename order, and treats each split as an independent processing unit.
  - **Run layout:** Each run writes into `runs/<run-id>/` with dedicated `articles/`, `redirect_aliases/`, `disambiguation/`, `manifests/`, `stats/`, `logs/`, and `temp/` subdirectories. Every run owns its own immutable audit context.
  - **Resume contract:** Split status is tracked in split-level manifests using only `pending`, `running`, `completed`, and `failed-threshold`. Resume decisions use manifest state rather than inferring completion from output files.
  - **Temporary-file policy:** The pipeline may use split-local spill files, checkpoints, and unfinalized shard files under `temp/`. Writing a fully decompressed XML dump or fully decompressed XML split as a normal execution step is out of scope.
  - **Page classification:** Classification order is fixed:
    1. `ignored` when `ns != 0`
    2. `redirect alias` when the page carries explicit redirect structure
    3. `disambiguation` when structure-first disambiguation signals match with conservative heuristic fallback
    4. `canonical article` for remaining main-namespace pages
  - **Canonical article schema:** Each article record contains exactly `page_id`, `title`, `revision_id`, `revision_timestamp`, `source_dump`, `source_url`, `clean_text`, and `text_length`.
  - **Redirect alias schema:** Each redirect record contains `redirect_title`, `canonical_title`, `source_dump`, and `source_url`.
  - **Disambiguation schema:** Each disambiguation record contains `page_id`, `title`, and `source_url`.
  - **`source_url` meaning:** `source_url` is a canonical Wikipedia page URL rather than dump-file provenance. Canonical article and disambiguation records derive `source_url` from their `title`. Redirect alias records derive `source_url` from `redirect_title`. Dump provenance remains captured separately by `source_dump` and run/split manifests rather than overloading `source_url` with dump-file locations.
  - **Clean-text policy:** Canonical article output is human-readable document text. Cleaning keeps section headings, paragraph boundaries, and simple list structure while removing templates, references, tables, file/image embeds, categories, navigation residue, and site-maintenance noise.
  - **Link policy:** Internal links keep readable anchor text rather than wiki markup. External links keep human-readable anchor text when present; non-semantic bare-link residue may be removed.
  - **Template policy:** The accepted first version does not attempt complete MediaWiki template expansion. Cleaning prefers structure-level noise removal and readable narrative preservation over rendering fidelity.
  - **Formatting policy:** `clean_text` uses normalized blank lines, normalized list bullets, trimmed trailing whitespace, collapsed repeated blank sections, and preserved Unicode text. The article title remains a top-level record field and is not required to be duplicated into `clean_text`.
  - **Failure policy:** Single-page failures default to fail-open behavior. Failed pages are skipped from canonical output, written to `logs/parse_failures.jsonl`, and counted in stats.
  - **Threshold policy:** The run upgrades to fail-fast when any configured threshold is crossed: global failure ratio/count, consecutive failure streak, or split-local failure ratio. Threshold values are runtime configuration, not hard-coded spec constants.
  - **Diagnostics on abort:** Threshold-triggered aborts must emit recent failure samples, error-type distribution, triggering threshold category, and affected split identity.
  - **Deterministic sharding:** Output partitioning uses split-aligned outer directories and deterministic rolling shards inside each split based on fixed record-count or uncompressed-byte thresholds. Output filenames, record order, and shard boundaries remain stable for the same input set and configuration.
  - **Serialization contract:** JSON key order, timestamp format, shard naming, and manifest update timing are fixed so repeated runs are reproducible and auditable.
  - **Technology selection:** The accepted first-version stack is Python script execution with streaming `.bz2` reads, `lxml.etree.iterparse` for XML, `mwparserfromhell` for wikitext-aware cleaning, and `zstandard` for shard compression.
- **Interactions:**
  1. The controller initializes a new run context and records immutable run metadata.
  2. Input discovery enumerates XML split files and assigns stable split identifiers.
  3. For each split in order, the controller sets split state to `running` and opens split-local artifact writers.
  4. Streaming XML extraction yields one page at a time with base page fields.
  5. Classification routes the page into `ignored`, `redirect alias`, `disambiguation`, or `canonical article`.
  6. Canonical pages pass through wikitext cleaning into `clean_text`; non-canonical outputs bypass the cleaning stage.
  7. Deterministic writers roll shard files as configured and finalize manifests/stats only after shard completion.
  8. Failures are logged per page; threshold monitors evaluate whether the run continues or aborts.
  9. Completed splits are marked `completed`; interrupted `running` splits are safely reset and restarted from split start during resume.
  10. The run ends with finalized run-level stats, manifests, and event logs.

## Validation
- **Checks:**
  - Spec review confirms this document contains only current preprocessing truth and does not redefine online ingestion/runtime contracts.
  - Sample-page validation verifies expected classification and readable `clean_text` output for representative canonical, redirect, disambiguation, and ignored pages.
  - Split-level validation verifies directory layout, deterministic shard rollover, manifest/status transitions, and split restart safety.
  - Re-run validation verifies identical record counts, shard names, and core manifest/stat outputs for the same input split and configuration.
  - Threshold validation verifies fail-open behavior for isolated page failures and fail-fast promotion when configured failure thresholds are exceeded.
- **Evidence:**
  - Passing sample-based and split-based verification runs.
  - Matching outputs across repeated deterministic test runs.
  - Logs and stats showing page-classification counts, failure distributions, and threshold-trigger diagnostics.
