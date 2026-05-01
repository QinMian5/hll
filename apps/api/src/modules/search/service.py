"""
Abstract: Search orchestration service for query embedding and knowledge lookups.
Out of scope: FastAPI transport wiring and direct database access.
"""

from __future__ import annotations

import logging

from core.errors import ErrorCode, InfrastructureError
from modules.knowledge_graph.ports import KnowledgeGraphReadPort
from modules.search.cache import SearchEmbeddingCachePort, SearchResponseCachePort
from modules.search.schema import MatchedCardResponse, SearchResponse
from shared.integrations import EmbeddingClientPort, EmbeddingServiceUnavailableError

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        *,
        knowledge_graph_read_port: KnowledgeGraphReadPort,
        embedding_client: EmbeddingClientPort,
        max_matched: int,
        max_connected: int,
        response_cache: SearchResponseCachePort | None = None,
        embedding_cache: SearchEmbeddingCachePort | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self._knowledge_graph_read_port = knowledge_graph_read_port
        self._embedding_client = embedding_client
        self._max_matched = max_matched
        self._max_connected = max_connected
        self._response_cache = response_cache
        self._embedding_cache = embedding_cache
        self._embedding_model = embedding_model

    async def search(self, query: str) -> SearchResponse:
        cached_response = await self._get_cached_response(query=query)
        if cached_response is not None:
            return cached_response

        query_embedding = await self._get_cached_embedding(query=query)
        if query_embedding is None:
            query_embedding = await self._embed_query(query=query)
            await self._set_cached_embedding(query=query, embedding=query_embedding)

        response = await self._search_with_embedding(query=query, query_embedding=query_embedding)
        await self._set_cached_response(query=query, response=response)
        return response

    async def _embed_query(self, *, query: str) -> list[float]:
        try:
            return await self._embedding_client.embed_text(query)
        except EmbeddingServiceUnavailableError as exc:
            raise InfrastructureError(
                code=ErrorCode.INFRA_EMBEDDING_SERVICE_UNAVAILABLE,
                message="Search dependency unavailable.",
                hint="Retry the search later.",
                safe_details={"dependency": "embedding_service"},
                log_details={"reason": str(exc)},
            ) from exc

    async def _search_with_embedding(
        self,
        *,
        query: str,
        query_embedding: list[float],
    ) -> SearchResponse:
        matched_records = await self._knowledge_graph_read_port.search_searchable_cards(
            query_text=query,
            query_embedding=query_embedding,
            limit=self._max_matched,
        )

        matched_cards = [
            MatchedCardResponse(
                node_id=item.node_id,
                current_version=item.current_version,
                title=item.title,
                content=item.content,
            )
            for item in matched_records
        ]
        connected_titles = await self._knowledge_graph_read_port.get_connected_titles(
            matched_node_ids=[item.node_id for item in matched_records],
            excluded_titles={item.title for item in matched_records},
            limit=self._max_connected,
        )

        return SearchResponse(
            matched_cards=matched_cards,
            connected_titles=connected_titles,
        )

    async def _get_cached_response(self, *, query: str) -> SearchResponse | None:
        if self._response_cache is None:
            return None
        try:
            return await self._response_cache.get(
                query=query,
                max_matched=self._max_matched,
                max_connected=self._max_connected,
            )
        except Exception as exc:
            _log_cache_failure(cache_name="search-response", operation="get", exc=exc)
            return None

    async def _set_cached_response(self, *, query: str, response: SearchResponse) -> None:
        if self._response_cache is None:
            return
        try:
            await self._response_cache.set(
                query=query,
                max_matched=self._max_matched,
                max_connected=self._max_connected,
                response=response,
            )
        except Exception as exc:
            _log_cache_failure(cache_name="search-response", operation="set", exc=exc)

    async def _get_cached_embedding(self, *, query: str) -> list[float] | None:
        if self._embedding_cache is None or self._embedding_model is None:
            return None
        try:
            return await self._embedding_cache.get(
                query=query,
                embedding_model=self._embedding_model,
            )
        except Exception as exc:
            _log_cache_failure(cache_name="search-embedding", operation="get", exc=exc)
            return None

    async def _set_cached_embedding(self, *, query: str, embedding: list[float]) -> None:
        if self._embedding_cache is None or self._embedding_model is None:
            return
        try:
            await self._embedding_cache.set(
                query=query,
                embedding_model=self._embedding_model,
                embedding=embedding,
            )
        except Exception as exc:
            _log_cache_failure(cache_name="search-embedding", operation="set", exc=exc)


def _log_cache_failure(*, cache_name: str, operation: str, exc: Exception) -> None:
    logger.warning(
        "Search cache failure.",
        extra={
            "cache_name": cache_name,
            "cache_operation": operation,
            "reason": str(exc),
        },
    )
