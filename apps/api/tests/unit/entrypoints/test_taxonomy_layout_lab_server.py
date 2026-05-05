"""
Abstract: Unit tests for the local taxonomy layout tuning HTTP app.
Out of scope: Production API router wiring and browser rendering behavior.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from entrypoints.ops.taxonomy_layout_lab_server import create_app
from modules.taxonomy.layout_lab import DEFAULT_LAYOUT_LAB_FIXTURE


def test_layout_lab_server_lists_fixtures() -> None:
    client = TestClient(create_app())

    response = client.get("/fixtures")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": DEFAULT_LAYOUT_LAB_FIXTURE,
            "node_count": 16,
            "edge_count": 18,
        }
    ]


def test_layout_lab_server_solves_fixture_with_parameter_overrides() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/solve",
        json={
            "fixtureName": DEFAULT_LAYOUT_LAB_FIXTURE,
            "params": {
                "seed_base_radius": 40.0,
                "seed_radius_step": 10.0,
                "simulation_ticks": 0,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["layout_version"] == "taxonomy-card-scope-layout-v1"
    assert body["layout_status"] == "ready"
    assert len(body["nodes"]) == 16
    assert len(body["edges"]) == 18
    assert body["nodes"][0]["x"] == 50.0
    assert body["edges"][0] == [1, 2, 1.0]


def test_layout_lab_server_rejects_unknown_fixture() -> None:
    client = TestClient(create_app())

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
    client = TestClient(create_app())

    response = client.get("/params/default")

    assert response.status_code == 200
    assert response.json()["radial_boundary_radius"] == 0.0
    assert response.json()["center_gravity_strength"] > 0.0
