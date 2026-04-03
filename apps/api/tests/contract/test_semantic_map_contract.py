"""
Abstract: Contract test for OpenAPI exposure of semantic-map routes.
Out of scope: Route runtime behavior and rebuild execution semantics.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_openapi_contains_semantic_map_paths(client: TestClient) -> None:
    assert isinstance(client.app, FastAPI)
    openapi = client.app.openapi()

    assert "/semantic-map/manifest/current" in openapi["paths"]
    assert (
        "/semantic-map/versions/{version}/tiles/regions/{semantic_level}/{z}/{x}/{y}"
        in openapi["paths"]
    )


@pytest.mark.contract
def test_semantic_map_openapi_includes_manifest_and_tile_success_responses(
    client: TestClient,
) -> None:
    assert isinstance(client.app, FastAPI)
    openapi = client.app.openapi()

    manifest_responses = openapi["paths"]["/semantic-map/manifest/current"]["get"]["responses"]
    tile_responses = openapi["paths"][
        "/semantic-map/versions/{version}/tiles/regions/{semantic_level}/{z}/{x}/{y}"
    ]["get"]["responses"]

    assert "200" in manifest_responses
    assert "200" in tile_responses
