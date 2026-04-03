"""
Abstract: Contract test for OpenAPI exposure of ingestion and search routes.
Out of scope: Route runtime behavior and worker-side execution semantics.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.contract
def test_openapi_contains_search_and_ingestion_paths(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()

    assert "/search" in openapi["paths"]
    assert "/cards" in openapi["paths"]


@pytest.mark.contract
def test_ingestion_openapi_includes_202_and_422_responses(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()

    responses = openapi["paths"]["/cards"]["post"]["responses"]
    assert "202" in responses
    assert "422" in responses
