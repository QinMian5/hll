"""
Abstract: Generate a focused Python client for repository-owned private API contracts.
Out of scope: General OpenAPI client generation and runtime service discovery.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from textwrap import dedent
from typing import Any, cast

SEARCH_PATH = "/api/v1/search"
CARD_PROPOSAL_PATH = "/api/v1/card-proposals"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openapi", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    openapi = _load_openapi(args.openapi)
    _validate_search_contract(openapi)
    _validate_card_proposal_contract(openapi)
    _write_generated_package(args.output_dir)


def _load_openapi(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"Missing OpenAPI source artifact: {path}")

    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)

    if not isinstance(loaded, dict):
        raise SystemExit("OpenAPI source artifact must be a JSON object.")

    return loaded


def _validate_search_contract(openapi: dict[str, Any]) -> None:
    paths = _require_mapping(openapi, "paths")
    search_path = _require_mapping(paths, SEARCH_PATH)
    search_get = _require_mapping(search_path, "get")

    parameters = search_get.get("parameters")
    if not isinstance(parameters, list):
        raise SystemExit(f"{SEARCH_PATH} GET must define parameters.")

    query_parameter = _find_query_parameter(parameters)
    if query_parameter.get("required") is not True:
        raise SystemExit(f"{SEARCH_PATH} query parameter must be required.")

    query_schema = _require_mapping(query_parameter, "schema")
    if query_schema.get("type") != "string" or query_schema.get("minLength") != 1:
        raise SystemExit(f"{SEARCH_PATH} query parameter must be a string with minLength=1.")

    responses = _require_mapping(search_get, "responses")
    response_200 = _require_mapping(responses, "200")
    content = _require_mapping(response_200, "content")
    json_content = _require_mapping(content, "application/json")
    response_schema = _require_mapping(json_content, "schema")
    if response_schema.get("$ref") != "#/components/schemas/SearchResponse":
        raise SystemExit(f"{SEARCH_PATH} 200 response must reference SearchResponse.")

    components = _require_mapping(openapi, "components")
    schemas = _require_mapping(components, "schemas")
    search_response = _require_mapping(schemas, "SearchResponse")
    matched_card = _require_mapping(schemas, "MatchedCardResponse")

    _validate_search_response_schema(search_response)
    _validate_matched_card_schema(matched_card)


def _find_query_parameter(parameters: list[object]) -> dict[str, Any]:
    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        mapping = cast(dict[str, Any], parameter)
        if mapping.get("in") == "query" and mapping.get("name") == "query":
            return mapping

    raise SystemExit(f"{SEARCH_PATH} must define required query parameter 'query'.")


def _validate_search_response_schema(schema: dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise SystemExit("SearchResponse must be an object schema.")

    required = schema.get("required")
    if required != ["matched_cards", "connected_titles"]:
        raise SystemExit(
            "SearchResponse required fields must be matched_cards and connected_titles."
        )

    properties = _require_mapping(schema, "properties")
    matched_cards = _require_mapping(properties, "matched_cards")
    matched_items = _require_mapping(matched_cards, "items")
    if matched_items.get("$ref") != "#/components/schemas/MatchedCardResponse":
        raise SystemExit("SearchResponse.matched_cards must contain MatchedCardResponse items.")

    connected_titles = _require_mapping(properties, "connected_titles")
    connected_items = _require_mapping(connected_titles, "items")
    if connected_items.get("type") != "string":
        raise SystemExit("SearchResponse.connected_titles must contain string items.")


def _validate_matched_card_schema(schema: dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise SystemExit("MatchedCardResponse must be an object schema.")

    required = schema.get("required")
    if required != ["node_id", "current_version", "title", "content"]:
        raise SystemExit(
            "MatchedCardResponse required fields must be node_id, "
            "current_version, title, and content."
        )

    properties = _require_mapping(schema, "properties")
    for field_name in ("node_id", "current_version"):
        field = _require_mapping(properties, field_name)
        if field.get("type") != "integer":
            raise SystemExit(f"MatchedCardResponse.{field_name} must be an integer.")
    for field_name in ("title", "content"):
        field = _require_mapping(properties, field_name)
        if field.get("type") != "string":
            raise SystemExit(f"MatchedCardResponse.{field_name} must be a string.")


def _validate_card_proposal_contract(openapi: dict[str, Any]) -> None:
    paths = _require_mapping(openapi, "paths")
    card_proposal_path = _require_mapping(paths, CARD_PROPOSAL_PATH)
    card_proposal_post = _require_mapping(card_proposal_path, "post")

    request_body = _require_mapping(card_proposal_post, "requestBody")
    request_content = _require_mapping(request_body, "content")
    request_json_content = _require_mapping(request_content, "application/json")
    request_schema_ref = _require_mapping(request_json_content, "schema").get("$ref")
    if request_schema_ref != "#/components/schemas/CardProposalCreateRequest":
        raise SystemExit(
            f"{CARD_PROPOSAL_PATH} request body must reference CardProposalCreateRequest."
        )

    responses = _require_mapping(card_proposal_post, "responses")
    response_201 = _require_mapping(responses, "201")
    response_content = _require_mapping(response_201, "content")
    response_json_content = _require_mapping(response_content, "application/json")
    response_schema_ref = _require_mapping(response_json_content, "schema").get("$ref")
    if response_schema_ref != "#/components/schemas/CardProposalResponse":
        raise SystemExit(f"{CARD_PROPOSAL_PATH} 201 response must reference CardProposalResponse.")

    components = _require_mapping(openapi, "components")
    schemas = _require_mapping(components, "schemas")
    request_schema = _require_mapping(schemas, "CardProposalCreateRequest")
    response_schema = _require_mapping(schemas, "CardProposalResponse")
    if request_schema.get("required") != ["proposal_type"]:
        raise SystemExit("CardProposalCreateRequest required fields are not current.")
    if response_schema.get("required") != [
        "id",
        "proposal_type",
        "status",
        "submitted_by_user_id",
        "reviewed_by_user_id",
        "review_note",
        "payload",
        "created_at",
        "updated_at",
        "reviewed_at",
    ]:
        raise SystemExit("CardProposalResponse required fields are not current.")


def _require_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"Expected object at key '{key}'.")
    return value


def _write_generated_package(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)

    package_dir = output_dir / "src" / "knowledge_contracts_client"
    package_dir.mkdir(parents=True)

    _write_text(output_dir / "pyproject.toml", _pyproject_content())
    _write_text(package_dir / "__init__.py", _init_content())
    _write_text(package_dir / "search.py", _search_client_content())
    _write_text(package_dir / "py.typed", "")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _pyproject_content() -> str:
    return dedent(
        """
        # abstract: Generated Python package metadata for private API contract clients.
        # out_of_scope: Handwritten runtime integration logic and external package publishing.
        [project]
        name = "knowledge-contracts-client"
        version = "0.1.0"
        description = "Generated Python contract client for repository-owned private APIs."
        requires-python = ">=3.14"
        dependencies = [
            "httpx>=0.28.1",
            "pydantic>=2.12.5",
        ]

        [build-system]
        requires = ["uv_build>=0.11.2,<0.12"]
        build-backend = "uv_build"

        [tool.uv.build-backend]
        module-name = ["knowledge_contracts_client"]
        """
    ).lstrip()


def _init_content() -> str:
    return dedent(
        '''
        """
        Abstract: Generated package exports for private API contract clients.
        Out of scope: Runtime service discovery and product-specific orchestration.
        """

        from knowledge_contracts_client.search import (
            MatchedCard,
            SearchClient,
            SearchClientError,
            SearchResponse,
            SearchUpstreamError,
            SearchValidationError,
        )

        __all__ = [
            "MatchedCard",
            "SearchClient",
            "SearchClientError",
            "SearchResponse",
            "SearchUpstreamError",
            "SearchValidationError",
        ]
        '''
    ).lstrip()


def _search_client_content() -> str:
    return dedent(
        '''
        """
        Abstract: Generated async client for the private search HTTP contract.
        Out of scope: MCP tool orchestration, authentication, quota, and service discovery.
        """

        from __future__ import annotations

        from typing import Any

        import httpx
        from pydantic import BaseModel, ConfigDict


        class SearchClientError(Exception):
            """Base error for generated search-client failures."""


        class SearchValidationError(SearchClientError):
            """Raised when the private search API rejects the request contract."""

            def __init__(self, *, status_code: int, body: object) -> None:
                super().__init__(f"Search API validation failed with status {status_code}.")
                self.status_code = status_code
                self.body = body


        class SearchUpstreamError(SearchClientError):
            """Raised when the private search API returns an unexpected status."""

            def __init__(self, *, status_code: int, body: object) -> None:
                super().__init__(f"Search API request failed with status {status_code}.")
                self.status_code = status_code
                self.body = body


        class MatchedCard(BaseModel):
            """Matched card returned by the private search API."""

            model_config = ConfigDict(extra="forbid")

            node_id: int
            current_version: int
            title: str
            content: str


        class SearchResponse(BaseModel):
            """Search response returned by the private search API."""

            model_config = ConfigDict(extra="forbid")

            matched_cards: list[MatchedCard]
            connected_titles: list[str]


        class SearchClient:
            """Async client for the private search API contract."""

            def __init__(
                self, *, base_url: str, http_client: httpx.AsyncClient | None = None
            ) -> None:
                self._base_url = base_url.rstrip("/")
                self._http_client = http_client or httpx.AsyncClient()
                self._owns_http_client = http_client is None

            async def aclose(self) -> None:
                if self._owns_http_client:
                    await self._http_client.aclose()

            async def search(self, query: str) -> SearchResponse:
                response = await self._http_client.get(
                    f"{self._base_url}/api/v1/search",
                    params={"query": query},
                )
                if response.status_code == 422:
                    raise SearchValidationError(
                        status_code=response.status_code,
                        body=_safe_response_body(response),
                    )
                if response.status_code < 200 or response.status_code >= 300:
                    raise SearchUpstreamError(
                        status_code=response.status_code,
                        body=_safe_response_body(response),
                    )

                return SearchResponse.model_validate(response.json())


        def _safe_response_body(response: httpx.Response) -> object:
            try:
                body: Any = response.json()
            except ValueError:
                return response.text
            return body
        '''
    ).lstrip()


if __name__ == "__main__":
    main()
