---
abstract: Operator-triggered taxonomy classification orchestration for incrementally assigning unclassified knowledge nodes through one Cursor session per node.
out_of_scope: Taxonomy tree persistence ownership, semantic-map snapshot rendering, and HTTP-triggered classification job APIs.
---

# Design: taxonomy-classification

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of preserving transition narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the `taxonomy_classification` module that incrementally classifies unassigned knowledge nodes by running one Cursor session per node and binding each node to one final taxonomy leaf.
- **Scope/Boundaries:** Covers operator-triggered batch selection, one-node session orchestration, Cursor tool-call contracts for progressive taxonomy traversal, and first-write assignment semantics. Excludes taxonomy tree persistence ownership, semantic-map rendering behavior, and HTTP-triggered job APIs.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Module boundaries remain explicit, persistent truth ownership stays in `knowledge_graph` and `taxonomy`, and behavior-changing design decisions stay synchronized in active specs.
- **Detail Commitments:** Classification execution is operator-triggered via script, defaults to concurrent execution with `max_workers=8`, processes unassigned nodes in `nodes.id ASC` order, supports optional `--limit`, and runs one Cursor session per node with `title + content` context only.
- **Update Rule:** Requirement-level constraints remain stable while classification orchestration behavior, tool contracts, and runtime/operator semantics are maintained here as implementation-facing truth.

## Design Approach
- **Approach:** Add a dedicated backend `taxonomy_classification` module that orchestrates incremental classification while keeping taxonomy truth and knowledge-node truth owned by their existing modules.
- **Key Elements:**
  - **Module ownership:** `apps/api/src/modules/taxonomy_classification` owns batch node selection orchestration, Cursor session orchestration, and tool-call boundaries exposed to Cursor for progressive taxonomy traversal.
  - **Dependency boundary:** `taxonomy_classification` consumes `knowledge_graph` service ports for node input data and consumes `taxonomy` service ports for taxonomy traversal and final assignment writes.
  - **Single-session rule:** One node is processed by exactly one Cursor session; one session handles one node end-to-end.
  - **Node context contract:** Cursor receives only the selected node's `title` and `content`.
  - **Progressive disclosure contract:** Cursor traverses taxonomy by repeatedly calling `list_children(parent_id)` until a suitable leaf is selected.
  - **Assignment contract:** Cursor calls `assign_leaf(node_id, leaf_id)` in-session to persist the final classification result.
  - **First-write rule:** `assign_leaf` is insert-only. If the node already has an assignment, the operation is rejected and does not overwrite existing truth.
  - **No failure-state persistence:** Failed node attempts do not write fallback state or error markers in persistent storage.
  - **Retry-by-next-run model:** Nodes left unassigned due to run-time failure remain eligible in the next operator run.
  - **No HTTP trigger surface:** First version exposes no API endpoint for classification job submission.

## Batch Execution Contract
- **Entrypoint:** one operator-facing script under `scripts/` triggers classification runs.
- **Selection set:** only nodes without rows in `node_taxonomy_assignments` are eligible.
- **Ordering:** eligible nodes are processed in `nodes.id ASC`.
- **Limit behavior:** `--limit N` processes the first `N` eligible nodes; when omitted, all eligible nodes are processed.
- **Concurrency default:** batch execution defaults to `max_workers=8`.
- **Concurrency override:** script arguments may override the worker count for a run.

## Cursor Tool Contract
- **`list_children(parent_id)`**
  - Input: nullable taxonomy parent id.
  - Output: direct child taxonomy nodes sorted by `name ASC`.
  - Purpose: progressive taxonomy traversal within one session.
- **`get_assignment(node_id)`**
  - Input: node id.
  - Output: existing final assignment or none.
  - Purpose: in-session assignment state checks and terminal verification.
- **`assign_leaf(node_id, leaf_id)`**
  - Input: knowledge node id and taxonomy leaf id.
  - Output: persisted final assignment record.
  - Enforcement:
    - rejects non-leaf ids;
    - rejects second-write attempts for already assigned nodes;
    - does not update prior assignments.

## Runtime Configuration
- Classification runtime configuration is independent from `apps/cli` reviewer configuration.
- API runtime settings remain sourced through `apps/api/src/core/config.py`.
- Classification settings include:
  - Cursor executable path.
  - Cursor workspace root for node sessions.
  - Cursor session timeout.
  - Cursor retry limit for malformed/invalid session outputs.
  - Default classification concurrency (`max_workers=8`).

## Operator Experience
- Operator execution is script-driven and machine-repeatable.
- Command UX follows repository style for local operator utilities:
  - typed request/result contracts using Pydantic models;
  - command-line argument handling using Click;
  - progress and summary output using Rich.

## Failure Handling
- Node-level run-time failures are isolated to the current node and do not stop the batch run.
- A failed node attempt leaves persistent classification truth unchanged.
- Assignment collisions on already-assigned nodes are treated as non-overwrite outcomes.
- Batch-level completion reports processed, assigned, and unchanged counts without introducing persisted workflow state.

## Validation
- **Checks:**
  - Batch selection tests verify unassigned-only filtering, `nodes.id ASC` ordering, and `--limit` behavior.
  - Tool-contract tests verify `list_children` ordering and `assign_leaf` first-write-only enforcement.
  - Integration tests verify non-leaf assignment rejection and already-assigned rejection without overwrite.
  - Session-runner tests verify one node maps to one Cursor session and in-session assignment write flow.
  - CLI/script tests verify Click argument handling and Rich progress output.
- **Evidence:**
  - Passing unit and integration tests for selection, traversal-tool contract, and assignment constraints.
  - Passing operator-script tests showing default `max_workers=8` behavior with optional overrides.
