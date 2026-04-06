---
abstract: Local operator-facing CLI design covering the external command contract, invocation behavior, and machine-consumable output for reviewed card submission.
out_of_scope: Internal review-agent implementation, internal graph orchestration, backend ingestion worker semantics, and knowledge-graph persistence internals.
---

# Design: cli

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the accepted V1 external design for a dedicated local CLI application that accepts a single knowledge card, performs reviewed submission, and exposes a stable operator-facing interface.
- **Scope/Boundaries:** Covers command name and arguments, operator-facing behavior, stdout JSON contract, exit-code contract, and external runtime configuration. Excludes internal review-agent design, internal graph/state design, backend ingestion implementation details, knowledge-graph persistence, retrieval-augmented review, memory systems, and rewrite-generation workflows.
- **Related Requirements:** R-001, R-002, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository governance stays unified, authoritative service interfaces remain single-sourced, module boundaries stay explicit, runtime behavior remains reproducible, and spec truth remains synchronized with accepted behavior.
- **Detail Commitments:** The repository contains a dedicated app at `apps/cli`. The app exposes one importable Python entrypoint for reviewed single-card submission and one CLI wrapper that accepts `--title` and `--content`, emits a minimal English JSON result to stdout, uses `0/1` exit codes, and issues the existing `POST /cards` ingestion call only after a full local review pass. Internal orchestration details are defined in `cli-review-orchestration.md`.
- **Update Rule:** Requirement-level constraints remain stable while this design document captures external command shape, operator contract, output schema, and app-local runtime boundaries. Internal workflow changes are projected into `cli-review-orchestration.md`.

## Inputs & Outputs
- **Inputs:**
  - Command-line parameters:
    - `--title`
    - `--content`
  - Runtime configuration loaded through app-local `pydantic-settings`.
- **Outputs:**
  - A minimal English JSON result written to stdout when the shared reviewed-submission flow returns a valid review result.
  - A process exit code that distinguishes only success vs. non-success from the local CLI responsibility boundary.
  - **Artifacts:**
    - A typed review result containing the fixed review dimensions:
      - `title_validity`
      - `title_content_alignment`
      - `title_style_validity`
      - `content_coherence`
      - `content_atomicity`
      - `content_latex_validity`

## Design Approach
- **Approach:** Use a dedicated local CLI app as both an importable reviewed-submission library boundary and an operator-facing command boundary. The app owns the shared single-card submission function, while the CLI itself remains only a thin wrapper that parses arguments and serializes the shared function result into terminal output.
- **Key Elements:**
  - **Shared Python entrypoint:** Accepts `title` and `content`, runs the same review-and-submit flow that the CLI uses, returns the structured local review result, and raises on local runtime failure.
  - **CLI entrypoint:** Accepts `--title` and `--content` as required parameters and wraps the shared Python entrypoint to normalize all terminal states into JSON stdout plus deterministic exit codes.
  - **Review result contract:** The CLI emits only an English `result` marker on success, and on failure emits only the failed review dimensions with their `reason` and fixed `hint`.
  - **Submission initiation:** The CLI issues the authoritative `POST /cards` call only after local review passes.
  - **JSON formatter:** Produces one stable minimal review JSON shape without wrapper metadata.
- **Interactions:**
  1. The CLI parses `--title` and `--content`.
  2. Internal orchestration performs local review over the current input.
  3. If one or more review dimensions fail, the process emits rejection JSON and exits without contacting the backend.
  4. If all review dimensions pass, the CLI issues the ingestion submission call.
  5. After the submission call is issued, the CLI ends without classifying downstream ingestion outcomes as part of its own contract.

## Response Contract
- When every review dimension passes, stdout contains only:
  - `result` with the fixed English value `passed`
- When one or more review dimensions fail, stdout contains only:
  - `result` with the fixed English value `failed`
  - `failures`, keyed only by failed dimension names
- Each failed dimension contains only:
  - `reason`
  - `hint`
- Exit codes are fixed as:
  - `0`: required input is present and every review dimension passes
  - `1`: any local non-success outcome, including invalid invocation, failed review dimension, or local runtime failure before submission is issued

## Runtime Configuration
- Runtime configuration is owned by the CLI app and loaded through `pydantic-settings`.
- The app configuration includes:
  - ingestion API base URL or absolute cards endpoint URL
  - selected reviewer backend identifier
  - reviewer request timeout
  - backend-specific reviewer settings for the selected backend
- The accepted first-version reviewer backends are:
  - a Cursor Agent backend that runs headless review through the local `cursor-agent` command with app-owned command, workspace, timeout, and retry settings
  - an OpenAI-compatible backend with model identifier, API key, and base URL settings
- Runtime modules inside the CLI app must not read environment variables directly outside the app-local config entrypoint.

## Failure Handling
- Invalid CLI invocation fails before the graph starts.
- Reviewer rejection is a successful local terminal outcome, not an exception path.
- The CLI never submits a card to the backend when the review result is rejected.
- The CLI does not classify or report downstream ingestion outcomes after the submission call is issued.

## Validation
- **Checks:**
  - Spec review confirms this document contains only external CLI behavior and defers internals to `cli-review-orchestration.md`.
  - CLI contract tests verify parameter parsing, stdout JSON shape, and fixed exit codes.
  - Submission-adapter tests verify the backend request shape remains exactly `title` plus `content`.
- **Evidence:**
  - Passing tests for CLI contract and submission adapter behavior.
  - Active specs show the CLI app boundary, repository placement, and system/module ownership without contradictions.
