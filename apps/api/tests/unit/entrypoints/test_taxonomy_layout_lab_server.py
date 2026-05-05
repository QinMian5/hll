"""
Abstract: Unit tests for the local taxonomy layout tuning HTTP app.
Out of scope: Production API router wiring and browser rendering behavior.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import entrypoints.ops.taxonomy_layout_lab_server as lab_server
from modules.taxonomy.dto import (
    TaxonomyCardScopeLayout,
    TaxonomyCardScopeLayoutEdge,
    TaxonomyCardScopeLayoutNode,
    TaxonomyCardScopeWorldBounds,
)
from modules.taxonomy.layout_lab import DEFAULT_LAYOUT_LAB_FIXTURE


def test_layout_lab_server_lists_fixtures() -> None:
    client = TestClient(lab_server.create_app())

    response = client.get("/fixtures")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": DEFAULT_LAYOUT_LAB_FIXTURE,
            "node_count": 1233,
            "edge_count": 2158,
        },
        {
            "name": "obsidian-sample",
            "node_count": 16,
            "edge_count": 18,
        },
    ]


def test_layout_lab_server_solves_fixture_with_parameter_overrides() -> None:
    client = TestClient(lab_server.create_app())

    response = client.post(
        "/solve",
        json={
            "fixtureName": "obsidian-sample",
            "params": {
                "seed_base_radius": 40.0,
                "seed_radius_step": 10.0,
                "simulation_ticks": 0,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["layout_version"] == "taxonomy-card-scope-layout-v2"
    assert body["layout_status"] == "ready"
    assert len(body["nodes"]) == 16
    assert len(body["edges"]) == 18
    assert body["nodes"][0]["x"] == 50.0
    assert body["edges"][0] == [1, 2, 1.0]


def test_layout_lab_server_rejects_unknown_fixture() -> None:
    client = TestClient(lab_server.create_app())

    response = client.post(
        "/solve",
        json={
            "fixtureName": "missing",
            "params": {},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Layout lab fixture 'missing' was not found."


def test_layout_lab_server_returns_default_params() -> None:
    client = TestClient(lab_server.create_app())

    response = client.get("/params/default")

    assert response.status_code == 200
    assert response.json() == {
        "alpha_min": 0.001,
        "center_gravity_strength": 0.1,
        "charge_strength": -180.0,
        "collision_radius": 16.0,
        "collision_strength": 0.92,
        "link_base_distance": 92.0,
        "link_base_strength": 1.05,
        "link_distance_strength_factor": 36.0,
        "link_strength_factor": 0.5,
        "radial_boundary_radius": 0.0,
        "radial_boundary_strength": 0.0,
        "seed_base_radius": 80.0,
        "seed_radius_step": 96.0,
        "simulation_ticks": 160,
        "velocity_retention": 0.55,
    }


def test_layout_lab_server_reuses_cached_solve_payload(monkeypatch: MonkeyPatch) -> None:
    solve_call_count = 0

    def fake_solve_fixture(**_kwargs: object) -> TaxonomyCardScopeLayout:
        nonlocal solve_call_count
        solve_call_count += 1
        return _make_layout()

    monkeypatch.setattr(lab_server, "solve_layout_lab_fixture", fake_solve_fixture)
    client = TestClient(lab_server.create_app())
    request_payload = {
        "fixtureName": "obsidian-sample",
        "params": {"simulation_ticks": 4},
    }

    first_response = client.post("/solve", json=request_payload)
    second_response = client.post("/solve", json=request_payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json() == first_response.json()
    assert solve_call_count == 1


def test_layout_lab_server_keeps_distinct_parameter_sets_uncached(
    monkeypatch: MonkeyPatch,
) -> None:
    solve_call_count = 0

    def fake_solve_fixture(**_kwargs: object) -> TaxonomyCardScopeLayout:
        nonlocal solve_call_count
        solve_call_count += 1
        return _make_layout()

    monkeypatch.setattr(lab_server, "solve_layout_lab_fixture", fake_solve_fixture)
    client = TestClient(lab_server.create_app())

    client.post(
        "/solve",
        json={"fixtureName": "obsidian-sample", "params": {"simulation_ticks": 4}},
    )
    client.post(
        "/solve",
        json={"fixtureName": "obsidian-sample", "params": {"simulation_ticks": 5}},
    )

    assert solve_call_count == 2


def test_layout_lab_solve_cache_coalesces_duplicate_inflight_builds() -> None:
    cache = lab_server._SolveResultCache()
    solve_started = threading.Event()
    release_solve = threading.Event()
    solve_call_count = 0

    def build_payload() -> dict[str, object]:
        nonlocal solve_call_count
        solve_call_count += 1
        solve_started.set()
        assert release_solve.wait(timeout=2)
        return {"layout_status": "ready"}

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_result = executor.submit(
            cache.get_or_build,
            key=("obsidian-sample", (("simulation_ticks", 4),)),
            build=build_payload,
        )
        assert solve_started.wait(timeout=2)
        second_result = executor.submit(
            cache.get_or_build,
            key=("obsidian-sample", (("simulation_ticks", 4),)),
            build=build_payload,
        )
        time.sleep(0.05)
        assert solve_call_count == 1
        release_solve.set()

    assert first_result.result() == {"layout_status": "ready"}
    assert second_result.result() == {"layout_status": "ready"}
    assert solve_call_count == 1


def _make_layout() -> TaxonomyCardScopeLayout:
    return TaxonomyCardScopeLayout(
        layout_version="taxonomy-card-scope-layout-v2",
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        world_bounds=TaxonomyCardScopeWorldBounds(
            min_x=0.0,
            min_y=0.0,
            max_x=10.0,
            max_y=10.0,
        ),
        nodes=[
            TaxonomyCardScopeLayoutNode(id=1, scope="inner", x=0.0, y=0.0),
            TaxonomyCardScopeLayoutNode(id=2, scope="outer", x=10.0, y=10.0),
        ],
        edges=[
            TaxonomyCardScopeLayoutEdge(
                source_node_id=1,
                target_node_id=2,
                strength=1.0,
            )
        ],
    )
