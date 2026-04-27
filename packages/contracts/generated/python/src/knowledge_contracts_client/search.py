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
