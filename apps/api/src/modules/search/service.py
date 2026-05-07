"""
Abstract: Search orchestration service for query embedding and knowledge lookups.
Out of scope: FastAPI transport wiring and direct database access.
"""

from __future__ import annotations

import hashlib
import logging
import time

from core.errors import ErrorCode, InfrastructureError
from modules.knowledge_graph.ports import KnowledgeGraphReadPort
from modules.search.cache import (
    SearchEmbeddingCachePort,
    SearchResponseCachePort,
    normalize_search_query,
)
from modules.search.schema import MatchedCardResponse, SearchResponse
from shared.integrations import EmbeddingClientPort, EmbeddingServiceUnavailableError

logger = logging.getLogger(__name__)

_SEARCH_TIMING_FIELDS = (
    "cache_get",
    "embedding_cache_get",
    "embedding",
    "retrieval",
    "connected_titles",
    "cache_set",
)


class SearchService:
    def __init__(
        self,
        *,
        knowledge_graph_read_port: KnowledgeGraphReadPort,
        embedding_client: EmbeddingClientPort,
        max_matched: int,
        max_connected: int,
        vector_candidate_pool_size: int,
        response_cache: SearchResponseCachePort | None = None,
        embedding_cache: SearchEmbeddingCachePort | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self._knowledge_graph_read_port = knowledge_graph_read_port
        self._embedding_client = embedding_client
        self._max_matched = max_matched
        self._max_connected = max_connected
        self._vector_candidate_pool_size = vector_candidate_pool_size
        self._response_cache = response_cache
        self._embedding_cache = embedding_cache
        self._embedding_model = embedding_model

    async def search(self, query: str) -> SearchResponse:
        total_start = time.perf_counter()
        timings = _empty_search_timings()
        status = "error"
        response_cache_hit = False
        embedding_cache_hit = False
        vector_candidate_count = 0
        matched_count = 0
        connected_title_count = 0

        try:
            stage_start = time.perf_counter()
            cached_response = await self._get_cached_response(query=query)
            timings["cache_get"] = _elapsed_ms(stage_start)
            if cached_response is not None:
                status = "cache_hit"
                response_cache_hit = True
                matched_count = len(cached_response.matched_cards)
                connected_title_count = len(cached_response.connected_titles)
                return cached_response

            stage_start = time.perf_counter()
            query_embedding = await self._get_cached_embedding(query=query)
            timings["embedding_cache_get"] = _elapsed_ms(stage_start)
            embedding_cache_hit = query_embedding is not None
            if query_embedding is None:
                stage_start = time.perf_counter()
                query_embedding = await self._embed_query(query=query)
                timings["embedding"] = _elapsed_ms(stage_start)
                await self._set_cached_embedding(query=query, embedding=query_embedding)

            stage_start = time.perf_counter()
            search_result = await self._knowledge_graph_read_port.search_searchable_cards(
                query_text=query,
                query_embedding=query_embedding,
                limit=self._max_matched,
                vector_candidate_limit=self._vector_candidate_pool_size,
            )
            timings["retrieval"] = _elapsed_ms(stage_start)
            vector_candidate_count = search_result.vector_candidate_count
            matched_records = search_result.matches

            matched_cards = [
                MatchedCardResponse(
                    node_id=item.node_id,
                    current_version=item.current_version,
                    title=item.title,
                    content=item.content,
                )
                for item in matched_records
            ]
            stage_start = time.perf_counter()
            connected_titles = await self._knowledge_graph_read_port.get_connected_titles(
                matched_node_ids=[item.node_id for item in matched_records],
                excluded_titles={item.title for item in matched_records},
                limit=self._max_connected,
            )
            timings["connected_titles"] = _elapsed_ms(stage_start)

            response = SearchResponse(
                matched_cards=matched_cards,
                connected_titles=connected_titles,
            )
            matched_count = len(response.matched_cards)
            connected_title_count = len(response.connected_titles)

            stage_start = time.perf_counter()
            await self._set_cached_response(query=query, response=response)
            timings["cache_set"] = _elapsed_ms(stage_start)
            status = "ok"
            return response
        finally:
            timings["total"] = _elapsed_ms(total_start)
            _log_search_timing(
                query=query,
                status=status,
                response_cache_hit=response_cache_hit,
                embedding_cache_hit=embedding_cache_hit,
                max_matched=self._max_matched,
                max_connected=self._max_connected,
                vector_candidate_pool_size=self._vector_candidate_pool_size,
                vector_candidate_count=vector_candidate_count,
                matched_count=matched_count,
                connected_title_count=connected_title_count,
                timings=timings,
            )

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

    async def _get_cached_response(self, *, query: str) -> SearchResponse | None:
        if self._response_cache is None or self._embedding_model is None:
            return None
        try:
            return await self._response_cache.get(
                query=query,
                embedding_model=self._embedding_model,
                max_matched=self._max_matched,
                max_connected=self._max_connected,
                vector_candidate_pool_size=self._vector_candidate_pool_size,
            )
        except Exception as exc:
            _log_cache_failure(cache_name="search-response", operation="get", exc=exc)
            return None

    async def _set_cached_response(self, *, query: str, response: SearchResponse) -> None:
        if self._response_cache is None or self._embedding_model is None:
            return
        try:
            await self._response_cache.set(
                query=query,
                embedding_model=self._embedding_model,
                max_matched=self._max_matched,
                max_connected=self._max_connected,
                vector_candidate_pool_size=self._vector_candidate_pool_size,
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


def _empty_search_timings() -> dict[str, float]:
    return dict.fromkeys(_SEARCH_TIMING_FIELDS, 0.0)


def _elapsed_ms(started_at: float) -> float:
    return max((time.perf_counter() - started_at) * 1000.0, 0.0)


def _search_query_log_hash(query: str) -> str:
    normalized_query = normalize_search_query(query)
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()[:16]


def _log_search_timing(
    *,
    query: str,
    status: str,
    response_cache_hit: bool,
    embedding_cache_hit: bool,
    max_matched: int,
    max_connected: int,
    vector_candidate_pool_size: int,
    vector_candidate_count: int,
    matched_count: int,
    connected_title_count: int,
    timings: dict[str, float],
) -> None:
    logger.info(
        "search.timing",
        extra={
            "search_status": status,
            "search_cache_hit": response_cache_hit,
            "search_embedding_cache_hit": embedding_cache_hit,
            "search_query_hash": _search_query_log_hash(query),
            "search_max_matched": max_matched,
            "search_max_connected": max_connected,
            "search_vector_candidate_pool_size": vector_candidate_pool_size,
            "search_vector_candidate_count": vector_candidate_count,
            "search_matched_count": matched_count,
            "search_connected_title_count": connected_title_count,
            "search_timing_cache_get_ms": timings["cache_get"],
            "search_timing_embedding_cache_get_ms": timings["embedding_cache_get"],
            "search_timing_embedding_ms": timings["embedding"],
            "search_timing_retrieval_ms": timings["retrieval"],
            "search_timing_connected_titles_ms": timings["connected_titles"],
            "search_timing_cache_set_ms": timings["cache_set"],
            "search_timing_total_ms": timings["total"],
        },
    )
