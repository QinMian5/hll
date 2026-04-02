---
abstract: FastAPI-focused unit and lightweight integration test governance for async endpoint verification, fixture reuse, and deterministic teardown.
out_of_scope: Database topology isolation policy, queue-worker runtime behavior, and non-HTTP algorithmic unit-test strategy.
---

# Design: fastapi-unit-test-governance

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the canonical FastAPI HTTP endpoint test style for maintainable, reusable, and deterministic tests.
- **Scope/Boundaries:** Covers async endpoint test execution model, shared fixture contracts, dependency-override lifecycle, and forbidden test patterns for HTTP endpoint tests.
- **Related Requirements:** R-001, R-004, R-005, R-006.

## Constraint Projection
- **Governing Constraints:**
  - R-001 requires one repository-wide testing governance contract.
  - R-004 requires clear boundaries between test infrastructure and module behavior checks.
  - R-005 requires reproducible local/CI test behavior.
  - R-006 requires behavior-facing decisions to stay synchronized in active specs.
- **Detail Commitments:**
  - HTTP endpoint tests SHALL run on `pytest` with `pytest-anyio` as the async execution contract.
  - HTTP endpoint tests SHALL use `httpx.AsyncClient` with `ASGITransport`.
  - HTTP endpoint tests SHALL use `@pytest.mark.anyio` and `await` all HTTP calls.
  - Shared fixture infrastructure SHALL be defined in `apps/api/tests/conftest.py` and SHALL expose:
    - `dependency_overrides` for per-module override injection.
    - `app` fixture that reuses `main.app`.
    - `async_client` fixture for async HTTP calls.
  - Teardown SHALL reset `app.dependency_overrides` to an empty dictionary after each test.
  - HTTP endpoint tests SHALL reuse the existing application construction from `main.py`.
  - HTTP endpoint tests SHALL NOT instantiate local `FastAPI()` apps in test modules.
  - HTTP endpoint tests SHALL NOT define ad-hoc middleware in test modules when equivalent middleware exists in `main.py`.
  - New HTTP endpoint tests SHALL follow this design for both `unit` and lightweight `integration` layers.
- **Update Rule:** Keep top-level quality constraints in requirements stable and update this document for framework-specific FastAPI test-governance details.

## Inputs & Outputs
- **Inputs:**
  - `requirements.md` governing constraints.
  - `07-quality-engineering.md` and `unit-test-best-practice.md` quality baseline.
  - FastAPI endpoint modules and endpoint test modules under `apps/api/tests/**`.
- **Outputs:**
  - Canonical endpoint-test writing rules for async HTTP verification.
  - Fixture and teardown contract for reusable test infrastructure.
- **Artifacts:**
  - `apps/api/tests/conftest.py`
  - `apps/api/tests/unit/modules/*/test_api.py`
  - `apps/api/tests/integration/*`
  - `apps/api/pyproject.toml`

## Design Approach
- **Approach:** Enforce one async-first endpoint-test path with centralized fixture ownership and deterministic cleanup.
- **Key Elements:**
  - Single async endpoint client abstraction: `async_client`.
  - Central dependency override injection through fixture composition.
  - Layer markers (`unit`, `integration`, `contract`) combined with `anyio` for async endpoint execution.
  - Endpoint assertions focus on HTTP contract behavior (status code and response shape).
- **Interactions:**
  - Test modules provide module-local `dependency_overrides`.
  - Shared `app` fixture applies overrides to `main.app`.
  - Shared teardown clears overrides.
  - `async_client` performs awaited HTTP calls against the shared app instance.

## Validation
- **Checks:**
  - `uv run --project apps/api pytest` passes for changed endpoint test modules.
  - `rg "TestClient\\(|FastAPI\\(" apps/api/tests/unit/modules apps/api/tests/integration` returns no endpoint-test violations.
  - `rg "@pytest.mark.anyio" apps/api/tests/unit/modules/*/test_api.py apps/api/tests/integration` confirms async marker coverage for endpoint tests.
  - Review verifies `apps/api/tests/conftest.py` owns teardown of `app.dependency_overrides`.
- **Evidence:**
  - Passing pytest output for endpoint test targets.
  - Search results showing async endpoint-test usage and no local app construction in endpoint test modules.
