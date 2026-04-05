---
abstract: Semantic-map module design for snapshot-based semantic-space artifacts, read contracts, and frontend rendering boundaries.
out_of_scope: Point-level rendering details beyond accepted phase slices, storage-engine tuning or partitioning strategy, and clustering-algorithm benchmark tuning.
---

# Design: semantic-map

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the semantic-map product module that turns authoritative taxonomy structure plus persisted knowledge embeddings into snapshot-based semantic-space artifacts and exposes stable read contracts for frontend semantic-map browsing.
- **Scope/Boundaries:** Covers backend semantic-map module ownership, snapshot publication model, semantic-map HTTP contracts, frontend feature boundaries, and staged delivery slices. Excludes storage-engine internals, authentication, and non-semantic-map product surfaces.
- **Related Requirements:** R-001, R-002, R-003, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository governance stays contract-driven and module boundaries stay explicit; frontend API access must consume authoritative generated contracts; behavior-changing module decisions must stay synchronized in active specs.
- **Detail Commitments:** Semantic-map browsing uses semantic-space snapshots as the primary visualization source; semantic-map data is published as versioned snapshots; frontend rendering uses `deck.gl` over a Cartesian 2D coordinate plane; frontend transport types are generated from FastAPI OpenAPI and consumed through generated client artifacts.
- **Update Rule:** Requirement-level governance remains stable while semantic-map contract shape, snapshot semantics, and rendering boundaries are maintained here as the implementation-facing source of truth.

## Inputs & Outputs
- **Inputs:**
  - Persisted taxonomy tree and final taxonomy-leaf assignments.
  - Persisted `knowledge_graph` nodes and embeddings.
  - Persisted relation truth owned by `knowledge_graph`.
  - Frontend viewport requests for semantic-map manifest and region tiles.
- **Outputs:**
  - Current semantic-map manifest for frontend bootstrapping.
  - Snapshot-pinned region and label tiles for frontend rendering.
  - Published semantic-map snapshots produced by background rebuild execution.
- **Artifacts:**
  - Semantic-map snapshot manifest metadata.
  - Semantic-map region geometry and recommended-label tile payloads.
  - Generated OpenAPI-derived frontend contract artifacts under `packages/contracts/generated`.

## Design Approach
- **Approach:** Build semantic-map browsing as a dedicated product module that reads taxonomy structure and graph-domain truth through service ports, precomputes snapshot artifacts asynchronously, and serves snapshot-pinned region and label tiles to a `deck.gl` frontend feature.
- **Key Elements:**
  - **Semantic-map module ownership:** `apps/api/src/modules/semantic_map` owns semantic-map read contracts, snapshot read orchestration, and snapshot rebuild orchestration. It does not own graph persistence truth.
  - **Persistence projection source:** `apps/api/src/modules/semantic_map/model.py` defines the accepted snapshot persistence shape on shared SQLAlchemy metadata. Alembic revisions are derived from registered metadata through governed autogenerate flow; migration files are not the schema source of truth.
  - **Snapshot persistence tables:** `semantic_map_snapshots` stores one published manifest row per internal auto-increment integer `id` and externally visible unique `version`, together with world bounds, default view, default semantic level, and `current` publication state. `semantic_map_region_tiles` stores snapshot-pinned region and recommended-label tile payloads with its own auto-increment integer `id` primary key plus a unique lookup key over `(snapshot_id, semantic_level, tile_z, tile_x, tile_y)`.
  - **Snapshot publication model:** Semantic-map artifacts are rebuilt in batch from persisted embeddings. Frontend browsing reads the latest successful snapshot through `manifest/current`, then pins subsequent tile reads to the returned snapshot `version`.
  - **Snapshot version format:** Phase 1 publishes snapshot `version` as `YYYYMMDD_HHMMSS_microseconds` so each rebuild has one sortable external version token with a built-in anti-collision suffix.
  - **Phase 1 schema-version token:** Until a separate schema-versioning policy is accepted, `schema_version` mirrors the published snapshot `version` token instead of using a hard-coded static string.
  - **Snapshot publish consistency:** Snapshot publication flips prior `current` rows off and publishes a new `current` snapshot only when the new snapshot manifest and region-tile payload set are written successfully.
  - **Rebuild initiation surface:** Phase 1 rebuild execution is initiated only through a dedicated operator command or script. No HTTP rebuild endpoint is exposed, and ingestion does not auto-enqueue snapshot rebuilds.
  - **High-level structure truth:** Semantic-map top-level structure comes from the persisted taxonomy tree rather than from embedding-only clustering. Semantic-map rebuild consumes taxonomy nodes and final node-to-leaf assignments as the structural truth for region hierarchy.
  - **Embedding role:** Persisted embeddings support spatial projection, local arrangement inside taxonomy-backed regions, and lower-level neighborhood organization. Embeddings do not define the authoritative top-level class hierarchy.
  - **Semantic level model:** Semantic levels are taxonomy-depth-driven rather than one fixed hand-authored set of three global semantic bands. Frontend semantic zoom must tolerate varying taxonomy depth.
  - **Phase 1 world normalization:** Rebuild normalizes projected coordinates into one fixed Cartesian world extent `[0.0, 0.0, 1000.0, 1000.0]`, with `default_view.target = [500.0, 500.0]` and `default_view.zoom = 0.0`.
  - **Empty-source behavior:** When no projection nodes are available, rebuild returns without publishing a new snapshot so the frontend continues to see the latest successful version or the explicit no-snapshot empty state.
  - **Semantic-space rendering model:** Frontend semantic-map browsing uses `DeckGL` with `OrthographicView` over a Cartesian 2D world. Region and label layers are the primary Phase 1 rendering outputs. Point and edge detail are deferred to later accepted slices.
  - **Contract generation rule:** FastAPI route and schema definitions are the only transport-contract source. OpenAPI export and generated TypeScript client/types under `packages/contracts` are the only frontend transport types used by `apps/web`.
  - **Frontend feature boundary:** `apps/web/src/features/semantic-map` owns semantic-map page composition, rendering engine code, generated-client API adapters, and feature-specific UI overlays. Reusable primitives move to `shared/**` only after demonstrated cross-feature reuse.
  - **Manifest role:** Semantic-map manifest remains the read-side bootstrap document for frontend rendering metadata, but accepted level semantics are derived from taxonomy depth rather than from an embedding-defined global hierarchy.
  - **Coordinate system:** Semantic-map contracts use one Cartesian 2D coordinate system with `x-right-y-up` axis semantics and `[min_x, min_y, max_x, max_y]` bounds formatting for world and tile bounds.
  - **Region geometry extensibility:** Region payloads expose `geometry` as a typed structure (`polygon` or `multi_polygon`).
  - **Label semantics:** Region naming truth and tile display recommendations are separate. `region_name` identifies the semantic region; tile `labels[]` contain the recommended text payloads for the current tile and current semantic level.
  - **Snapshot consistency:** A browsing session may keep reading one snapshot `version` while a newer snapshot is published. Rebuild failures do not replace the current snapshot.
  - **Accepted delivery slices:**
    - **Phase 1:** manifest, region tiles, label tiles, pan/zoom, semantic-level transitions, debug HUD, and snapshot-backed frontend rendering.
    - **Phase 2:** atomic knowledge-point rendering and detail inspection.
    - **Phase 3:** local edge rendering, focus-driven graph detail, and advanced performance or visual refinements.
- **Interactions:**
  - Ingestion persists knowledge truth through the existing async write path.
  - Background semantic-map rebuild execution reads persisted taxonomy truth through `taxonomy` service ports, reads persisted knowledge truth through `knowledge_graph` service ports, and publishes a new snapshot on success.
  - Frontend requests `GET /semantic-map/manifest/current` to discover the latest successful snapshot and rendering metadata.
  - Frontend requests `GET /semantic-map/versions/{version}/tiles/regions/{semantic_level}/{z}/{x}/{y}` for region and recommended-label payloads.
  - Frontend renders semantic-map content through `deck.gl` and keeps transport-contract handling inside generated-client adapters rather than duplicating schema definitions.

## API Contract

### Manifest Endpoint
- Route: `GET /semantic-map/manifest/current`
- Success response includes:
  - `version`
  - `schema_version`
  - `built_at`
  - `coordinate_system.kind`
  - `coordinate_system.axis_direction`
  - `coordinate_system.bounds_format`
  - `world_bounds`
  - `tile_size`
  - `max_zoom`
  - `default_view.target`
  - `default_view.zoom`
  - `default_semantic_level`
  - `semantic_levels[]` entries with `level`, stable identifier, display name, zoom-band bounds, region role, and child-content role
- Failure behavior:
  - Returns `404` when no successful semantic-map snapshot is available.

### Region Tile Endpoint
- Route: `GET /semantic-map/versions/{version}/tiles/regions/{semantic_level}/{z}/{x}/{y}`
- Success response includes:
  - `schema_version`
  - `version`
  - `semantic_level`
  - `tile.z`
  - `tile.x`
  - `tile.y`
  - `tile.tile_bounds`
  - `tile.bounds_format`
  - Optional lightweight `stats.region_count`
  - Optional lightweight `stats.label_count`
  - `regions[]` entries with:
    - stable `id`
    - `parent_id`
    - `region_name`
    - `centroid`
    - `bbox`
    - typed `geometry`
    - `display_rank`
    - `children_available`
  - `labels[]` entries with:
    - stable `id`
    - `region_id`
    - recommended display `text`
    - `position`
    - `label_rank`
    - `font_size`
- Failure behavior:
  - Returns `404` for unknown snapshot `version`.
  - Returns `400` for invalid semantic-level or tile-path arguments.
  - Returns `200` with empty `regions` and `labels` when the requested tile contains no semantic-map content.

## Validation
- **Checks:**
  - Active specs describe semantic-map browsing as the primary frontend visualization surface.
  - FastAPI exposes semantic-map manifest and snapshot-pinned tile endpoints with OpenAPI export enabled.
  - Generated TypeScript contracts under `packages/contracts/generated` include semantic-map client and types consumed by `apps/web`.
  - Frontend renders region and label tiles through `deck.gl` without hand-written transport schema duplication.
  - Semantic-map browsing stays stable when no current snapshot exists, when a tile is empty, and when a newer snapshot is published after the current page load.
  - Module-boundary checks prevent `semantic_map` from importing `knowledge_graph` persistence models or repositories directly.
- **Evidence:**
  - Passing contract tests for manifest and tile endpoints.
  - Passing architecture checks covering `semantic_map` dependency boundaries.
  - Frontend verification showing pan, zoom, semantic-level transitions, and snapshot-pinned tile reads against generated contracts.
