"""
Abstract: Unit tests for the search HTTP route contract.
Out of scope: Embedding integration and database retrieval behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from httpx import AsyncClient

from entrypoints.api import providers as api_providers
from modules.search.schema import MatchedCardResponse, SearchResponse

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


@dataclass(slots=True)
class _FakeSearchService:
    async def search(self, query: str) -> SearchResponse:
        assert query == "hello world"
        return SearchResponse(
            matched_cards=[
                MatchedCardResponse(title="Card A", content="Alpha"),
                MatchedCardResponse(title="Card B", content="Beta"),
            ],
            connected_titles=["Card C"],
        )


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {
        api_providers.get_search_service: lambda: _FakeSearchService(),
    }


@pytest.mark.anyio
async def test_search_route_returns_expected_payload_shape(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/search", params={"query": "hello world"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected_titles"] == ["Card C"]
    assert payload["matched_cards"] == [
        {"title": "Card A", "content": "Alpha"},
        {"title": "Card B", "content": "Beta"},
    ]


@pytest.mark.anyio
async def test_search_route_rejects_empty_query(async_client: AsyncClient) -> None:
    response = await async_client.get("/search", params={"query": ""})

    assert response.status_code == 422
