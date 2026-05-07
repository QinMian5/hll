"""
Abstract: Contract test for OpenAPI exposure of ingestion and search routes.
Out of scope: Route runtime behavior and worker-side execution semantics.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _single_value_schema_value(schema: dict[str, object]) -> str:
    if "const" in schema:
        value = schema["const"]
        assert isinstance(value, str)
        return value
    enum = schema["enum"]
    assert enum == ["taxonomy_node"]
    return "taxonomy_node"


@pytest.mark.contract
def test_openapi_contains_search_and_ingestion_paths(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()

    assert "/api/v1/search" in openapi["paths"]
    assert "/api/v1/cards" in openapi["paths"]
    assert "/api/v1/cards/{node_id}/suggested-edits" in openapi["paths"]
    assert "/api/v1/taxonomy/view/path/{route_path}" in openapi["paths"]


@pytest.mark.contract
def test_taxonomy_view_openapi_includes_route_path_contract(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()
    operation = openapi["paths"]["/api/v1/taxonomy/view/path/{route_path}"]["get"]
    response_schema_ref = operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    response_schema = openapi["components"]["schemas"][response_schema_ref.rsplit("/", 1)[-1]]
    branch_schema_ref = response_schema["oneOf"][0]["$ref"]
    branch_schema = openapi["components"]["schemas"][branch_schema_ref.rsplit("/", 1)[-1]]
    current_scope_schema_name = branch_schema["properties"]["current_scope"]["$ref"]
    current_scope_schema = openapi["components"]["schemas"][
        current_scope_schema_name.rsplit("/", 1)[-1]
    ]

    assert {"route_slug", "route_path"} <= set(current_scope_schema["required"])


@pytest.mark.contract
def test_taxonomy_card_scope_openapi_includes_layout_status(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()
    card_scope_schema = openapi["components"]["schemas"]["TaxonomyNodeCardScopeViewResponse"]
    layout_slice_schema = openapi["components"]["schemas"]["TaxonomyCardScopeLayoutSliceResponse"]

    assert "layout_status" in card_scope_schema["required"]
    assert card_scope_schema["properties"]["layout_status"]["enum"] == ["ready", "refreshing"]
    assert "layout_status" in layout_slice_schema["required"]
    assert layout_slice_schema["properties"]["layout_status"]["enum"] == ["ready", "refreshing"]


@pytest.mark.contract
def test_taxonomy_view_openapi_scope_kind_is_real_taxonomy_node_only(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()
    scope_schema = openapi["components"]["schemas"]["TaxonomyViewScopeResponse"]
    layout_slice_schema = openapi["components"]["schemas"]["TaxonomyCardScopeLayoutSliceResponse"]

    assert _single_value_schema_value(scope_schema["properties"]["scope_kind"]) == "taxonomy_node"
    assert (
        _single_value_schema_value(layout_slice_schema["properties"]["scope_kind"])
        == "taxonomy_node"
    )


@pytest.mark.contract
def test_search_openapi_matched_cards_include_version_identity_fields(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()
    matched_card_schema = openapi["components"]["schemas"]["MatchedCardResponse"]

    assert {"node_id", "current_version", "title", "content"} <= set(
        matched_card_schema["properties"]
    )
    assert {"node_id", "current_version", "title", "content"} <= set(
        matched_card_schema["required"]
    )


@pytest.mark.contract
def test_suggested_edit_openapi_includes_create_contract(
    client: TestClient,
) -> None:
    openapi = client.app.openapi()
    operation = openapi["paths"]["/api/v1/cards/{node_id}/suggested-edits"]["post"]

    assert "201" in operation["responses"]
    request_schema_name = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    response_schema_name = operation["responses"]["201"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    request_schema = openapi["components"]["schemas"][request_schema_name.rsplit("/", 1)[-1]]
    response_schema = openapi["components"]["schemas"][response_schema_name.rsplit("/", 1)[-1]]
    assert {"base_version", "suggested_title", "suggested_content", "reason"} <= set(
        request_schema["required"]
    )
    assert "suggested_by_user_id" not in request_schema["properties"]
    assert {
        parameter["name"] for parameter in operation["parameters"] if parameter["in"] == "header"
    } >= {"X-Knowledge-Suggested-By-User-Id"}
    assert {"id", "node_id", "base_version", "status", "created_at"} <= set(
        response_schema["required"]
    )


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
    response_schema_name = responses["202"]["content"]["application/json"]["schema"]["$ref"]
    response_schema = openapi["components"]["schemas"][response_schema_name.rsplit("/", 1)[-1]]
    assert response_schema["properties"]["ingestion_id"]["type"] == "integer"
