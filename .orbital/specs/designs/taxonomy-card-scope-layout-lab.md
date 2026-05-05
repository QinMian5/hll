---
abstract: Local taxonomy card-scope layout tuning lab that reuses the production backend solver and production deck.gl renderer path.
out_of_scope: Public web routes, BFF/API product endpoints, production runtime topology, taxonomy tree mutation, and graph data classification policy.
---

# Design: taxonomy-card-scope-layout-lab

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Provide a local operator-facing tuning surface for selecting card-scope graph layout parameters that produce an Obsidian-like final static distribution while preserving production rendering fidelity.
- **Scope/Boundaries:** Covers the local lab runner, lab fixture graph inputs, card-scope layout parameter schema, parameterized use of the production taxonomy layout solver, reuse of the production deck.gl leaf graph renderer path, preview interaction controls, preset export, and validation expectations. Excludes public app navigation, web BFF endpoints, FastAPI product endpoints, OpenAPI generation, deployment topology, taxonomy assignment/classification behavior, and production graph data mutation.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:** Repository governance keeps local tooling, backend taxonomy layout ownership, frontend rendering ownership, and spec synchronization explicit. Runtime reproducibility requires deterministic fixture inputs, deterministic solver output for a given parameter set, and clear validation commands. Module boundaries require the lab to reuse production-owned units through explicit interfaces instead of duplicating layout or rendering logic.
- **Detail Commitments:** The lab uses the production Python card-scope layout solver with a parameter object and uses the production deck.gl leaf renderer path for graph presentation. It runs through a local development entrypoint that is not registered in the shared app router, not exposed through the web BFF, not included in OpenAPI, and not part of production Compose. The lab provides sliders for layout parameters, deterministic fixture graph selection, live preview requests, visible compute errors, layout quality metrics, and a copyable preset JSON payload for promotion into a production layout preset.
- **Update Rule:** Requirements remain stable at the repository-governance layer while lab entrypoint behavior, parameter schema, fixture ownership, production renderer reuse, and tuning validation rules are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Deterministic fixture graphs containing card-scope nodes, `inner` or `outer` scope markers, undirected edge pairs, and edge strength values.
  - A layout parameter object for the backend card-scope solver, including simulation tick count, velocity retention, link distance, link strength, charge, collision, center gravity, seed radius, and radial boundary controls.
  - A local browser viewport size for the production deck.gl leaf scene.
- **Outputs:**
  - A rendered graph preview using the same leaf deck.gl scene component family as the production card-scope renderer.
  - Layout quality metrics for comparing parameter sets, including bounds aspect ratio, node overlap count, edge length percentiles, disconnected component spread, isolated-node radial distribution, and approximate world density.
  - A copyable parameter preset JSON payload with stable key names and numeric values.
- **Artifacts:**
  - `/Users/mianqin/Code/knowledge/apps/api/src/modules/taxonomy/layout.py`
  - `/Users/mianqin/Code/knowledge/apps/api/tests/unit/modules/taxonomy/test_layout.py`
  - `/Users/mianqin/Code/knowledge/apps/api/src/entrypoints/ops/taxonomy_layout_lab_server.py`
  - `/Users/mianqin/Code/knowledge/apps/api/tests/unit/entrypoints/test_taxonomy_layout_lab_server.py`
  - `/Users/mianqin/Code/knowledge/apps/web/layout-lab.html`
  - `/Users/mianqin/Code/knowledge/apps/web/src/dev/taxonomy-layout-lab/`
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/leaf/`
  - `/Users/mianqin/Code/knowledge/scripts/taxonomy-layout-lab.sh`

## Design Approach
- **Approach:** Use a local two-part lab: a Python lab server computes layouts by calling the production taxonomy card-scope solver with caller-supplied parameters, and a standalone Vite/React lab page renders the returned layout through production leaf deck.gl scene components and helpers. The lab is optimized for fast local tuning while preserving solver and renderer fidelity for the final static graph shape.
- **Key Elements:**
  - **Parameterized solver boundary:** The card-scope layout builder accepts a typed layout-parameter object. Production callers use an explicit production preset. Lab callers submit temporary parameter objects. The solver remains deterministic for the same graph fixture and parameter object.
  - **Obsidian-like static layout goal:** Layout tuning prioritizes a final static force-directed distribution with global visual roundness, uniform orphan placement, clear node separation, bounded hub spokes, and stable world bounds. The lab does not model Obsidian animation timing or animated startup behavior.
  - **Center gravity rule:** The layout solver owns a per-node center gravity force that pulls every node toward the layout origin. This force is distinct from a centroid recentering step and is part of the parameterized force balance.
  - **Radial boundary rule:** The layout solver owns a soft radial boundary force that limits long tails without pinning every node to a ring. The boundary force is parameterized separately from center gravity and collision.
  - **Fixture ownership:** Lab fixtures are static, deterministic graph inputs. They cover small sanity graphs, medium hub-plus-component graphs, and large card-scope graphs representative of real taxonomy leaves. Fixture ids remain stable so parameter comparisons can be repeated.
  - **Local server boundary:** The lab server is a local operator entrypoint. It returns fixture directories, computes layout previews, and reports validation errors as visible structured responses. It does not mutate PostgreSQL, Redis, taxonomy assignments, layout read-model tables, or production caches.
  - **Production renderer reuse:** The lab page imports production leaf renderer primitives, including deck.gl scene assembly, scene-model helpers, viewport helpers, zoom-control behavior, leaf rendering constants, and title-label rendering behavior. The lab may use a small adapter to shape lab layout payloads into the same `LeafSceneModel` consumed by `LeafDeckScene`, but it does not implement an alternate graph renderer.
  - **Standalone web entry:** The lab page uses a standalone Vite entry and is not registered with `createAppRouter`. It does not render the shared `AppShell`, does not call `/web-api/*`, and does not rely on session or quota state.
  - **Initial viewport stability:** The lab preview fits the selected fixture when that fixture is first rendered, then preserves that initial viewport input while the same fixture is re-solved with different parameters. Re-solving a fixture updates production-rendered nodes and edges without forcing the deck scene back to a fixed fit-to-bounds view. Switching to a different fixture resets the initial viewport from that fixture's returned bounds.
  - **Interactive controls:** Sliders cover each numeric parameter with explicit min, max, step, current value, and reset behavior. Parameter changes are debounced and stale preview responses are ignored so older computations cannot overwrite newer results.
  - **Default tuning profile:** The lab default parameter profile matches the production Obsidian-like large-graph preset for `science/physics/heat/thermodynamics`: `seed_base_radius=80`, `seed_radius_step=96`, `simulation_ticks=160`, `velocity_retention=0.55`, `link_base_distance=92`, `link_distance_strength_factor=36`, `link_base_strength=1.05`, `link_strength_factor=0.5`, `charge_strength=-180`, `collision_radius=16`, `collision_strength=0.92`, `center_gravity_strength=0.10`, `radial_boundary_radius=0`, and `radial_boundary_strength=0`. This preset preserves the round seeded field while shortening connected-node distances and lowering long-edge tails compared with the earlier production force balance.
  - **Preset export:** The lab displays the current parameter object as formatted JSON and provides a copy action. The exported preset uses backend parameter key names so the selected values can be promoted to the production preset without translation.
  - **Failure visibility:** Invalid parameter sets, failed lab server calls, and solver errors are shown in the lab page. The lab does not silently retain stale output as if it were a successful preview.
- **Interactions:**
  - Starting the lab runs the local Python lab server and the standalone Vite lab entry.
  - The lab page requests available fixture metadata and loads the selected fixture.
  - Moving a slider updates the pending parameter object and schedules a preview compute request.
  - The lab server validates the parameter object, calls the production Python solver with the selected fixture, computes metrics, and returns the layout payload plus metrics.
  - The lab page adapts the returned layout payload into the production leaf scene model and renders it through `LeafDeckScene`.
  - Copying a preset exports the current parameter object for review and production-preset adoption.

## Validation
- **Checks:**
  - Backend unit tests verify layout parameter parsing, production preset determinism, lab parameter overrides, per-node center gravity behavior, radial boundary behavior, and rejection of invalid parameter values.
  - Backend lab-server tests verify fixture listing, preview computation, structured validation errors, non-mutation of production read-model/cache paths, and stable metrics for fixture inputs.
  - Frontend unit tests verify the lab page maps slider values into the backend parameter object, ignores stale preview responses, displays compute errors, renders metrics, and exports copyable preset JSON.
  - Frontend component tests verify the lab preview path uses production `LeafDeckScene` and production leaf scene helpers instead of an alternate renderer, keeps the initial viewport stable across same-fixture re-solves, and resets the initial viewport when the selected fixture changes.
  - Type checks verify lab payload types and production renderer adapters remain explicit and narrow.
  - Manual browser verification compares small, medium, and large fixtures while sliders update the production deck.gl preview within the local lab.
- **Evidence:**
  - Passing targeted backend tests for `modules/taxonomy/layout.py` and the lab server entrypoint.
  - Passing targeted frontend tests for the lab entry and production renderer reuse.
  - Passing project lint/type checks for changed backend and frontend paths.
  - Browser-level screenshots or screen recordings showing production deck.gl-rendered fixture previews for at least three fixture sizes and a copied preset JSON payload.
