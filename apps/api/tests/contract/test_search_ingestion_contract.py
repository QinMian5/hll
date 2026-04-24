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

    assert "/api/v1/search" in openapi["paths"]
    assert "/api/v1/cards" in openapi["paths"]


@pytest.mark.contract
def test_ingestion_openapi_includes_idempotency_header_and_responses(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()

    operation = openapi["paths"]["/api/v1/cards"]["post"]
    parameters = operation["parameters"]
    idempotency_parameters = [
        parameter
        for parameter in parameters
        if parameter["in"] == "header" and parameter["name"] == "Idempotency-Key"
    ]

    assert idempotency_parameters
    assert idempotency_parameters[0]["required"] is False

    responses = operation["responses"]
    assert "202" in responses
    assert "409" in responses
    assert "422" in responses
