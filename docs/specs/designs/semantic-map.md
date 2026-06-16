---
abstract: Frozen baseline record for the legacy semantic-map snapshot architecture.
out_of_scope: Active product-surface ownership, implementation planning, and runtime behavior governance.
---

# Design: semantic-map (Frozen)

## Frozen Baseline
- **State:** Frozen, removed from active roadmap.
- **Frozen at commit:** `bc941cdeaeed1a67492e5dec95d47e1b696cf4f5`
- **Frozen on:** 2026-04-06
- **Reason:** Product interaction uses taxonomy-query-driven drill-down browsing. Legacy semantic-map rebuild, snapshot, tile contracts, and persistence are no longer active truth.

## Historical Scope (Read-Only)
- Legacy semantic-map covered snapshot build/rebuild orchestration, snapshot/tile read contracts, and deck.gl visualization.
- This document is retained only as a git-locatable historical anchor.

## Active Truth Routing
- Current browsing architecture is governed by:
  - `designs/taxonomy.md`
  - `designs/01-system-modules.md`
  - `designs/knowledge-ingestion-search-orchestration.md`
  - `designs/05-technology-stack-selection.md`
  - `designs/08-persistence-schema-projection.md`
  - `designs/taxonomy-view-shell.md`
  - `designs/taxonomy-view-layouts.md`

## Validation
- No new implementation work or planning shall originate from this frozen document.
- Any behavior-changing work must follow active design documents listed above.
