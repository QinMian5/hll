"""
Abstract: Internal search adapter backed by the generated private API client.
Out of scope: MCP protocol registration, authentication, quota, and usage accounting.
"""

from __future__ import annotations

from knowledge_contracts_client import SearchClient, SearchResponse


class InternalSearchService:
    def __init__(self, *, client: SearchClient) -> None:
        self._client = client

    async def search(self, query: str) -> SearchResponse:
        return await self._client.search(query)
