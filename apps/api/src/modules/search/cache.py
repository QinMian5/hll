"""
Abstract: Search-specific Redis cache keys and payload adapters.
Out of scope: Search ranking orchestration and API dependency wiring.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from modules.search.schema import SearchResponse
from shared.cache import JsonRedisCache, RedisJsonProtocol

SEARCH_RESPONSE_CACHE_SCHEMA_VERSION = "v1"
SEARCH_EMBEDDING_CACHE_SCHEMA_VERSION = "v1"
SEARCH_ALGORITHM_VERSION = "hybrid-rrf-title-boost-ann-pool-v2"


class SearchResponseCachePort(Protocol):
    async def get(
        self,
        *,
        query: str,
        embedding_model: str,
        max_matched: int,
        max_connected: int,
        vector_candidate_pool_size: int,
    ) -> SearchResponse | None: ...

    async def set(
        self,
        *,
        query: str,
        embedding_model: str,
        max_matched: int,
        max_connected: int,
        vector_candidate_pool_size: int,
        response: SearchResponse,
    ) -> None: ...


class SearchEmbeddingCachePort(Protocol):
    async def get(self, *, query: str, embedding_model: str) -> list[float] | None: ...

    async def set(self, *, query: str, embedding_model: str, embedding: list[float]) -> None: ...


class _SearchEmbeddingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embedding: list[float]


def normalize_search_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip()).casefold()


def search_response_cache_key(
    *,
    query: str,
    embedding_model: str,
    max_matched: int,
    max_connected: int,
    vector_candidate_pool_size: int,
) -> str:
    digest = _stable_digest(
        {
            "query": normalize_search_query(query),
            "embedding_model": embedding_model,
            "search_algorithm_version": SEARCH_ALGORITHM_VERSION,
            "max_matched": max_matched,
            "max_connected": max_connected,
            "vector_candidate_pool_size": vector_candidate_pool_size,
        }
    )
    return f"knowledge:api:search-response:{SEARCH_RESPONSE_CACHE_SCHEMA_VERSION}:{digest}"


def search_embedding_cache_key(*, query: str, embedding_model: str) -> str:
    digest = _stable_digest(
        {
            "query": normalize_search_query(query),
            "embedding_model": embedding_model,
        }
    )
    return (
        "knowledge:api:search-embedding:"
        f"{SEARCH_EMBEDDING_CACHE_SCHEMA_VERSION}:{embedding_model}:{digest}"
    )


class SearchRedisResponseCache:
    def __init__(self, *, redis: RedisJsonProtocol, ttl_seconds: int) -> None:
        self._cache = JsonRedisCache(redis=redis)
        self._ttl_seconds = ttl_seconds

    async def get(
        self,
        *,
        query: str,
        embedding_model: str,
        max_matched: int,
        max_connected: int,
        vector_candidate_pool_size: int,
    ) -> SearchResponse | None:
        return await self._cache.get_model(
            key=search_response_cache_key(
                query=query,
                embedding_model=embedding_model,
                max_matched=max_matched,
                max_connected=max_connected,
                vector_candidate_pool_size=vector_candidate_pool_size,
            ),
            model_type=SearchResponse,
        )

    async def set(
        self,
        *,
        query: str,
        embedding_model: str,
        max_matched: int,
        max_connected: int,
        vector_candidate_pool_size: int,
        response: SearchResponse,
    ) -> None:
        await self._cache.set_model(
            key=search_response_cache_key(
                query=query,
                embedding_model=embedding_model,
                max_matched=max_matched,
                max_connected=max_connected,
                vector_candidate_pool_size=vector_candidate_pool_size,
            ),
            value=response,
            ttl_seconds=self._ttl_seconds,
        )


class SearchRedisEmbeddingCache:
    def __init__(self, *, redis: RedisJsonProtocol, ttl_seconds: int) -> None:
        self._cache = JsonRedisCache(redis=redis)
        self._ttl_seconds = ttl_seconds

    async def get(self, *, query: str, embedding_model: str) -> list[float] | None:
        payload = await self._cache.get_model(
            key=search_embedding_cache_key(query=query, embedding_model=embedding_model),
            model_type=_SearchEmbeddingPayload,
        )
        if payload is None:
            return None
        return payload.embedding

    async def set(self, *, query: str, embedding_model: str, embedding: list[float]) -> None:
        await self._cache.set_model(
            key=search_embedding_cache_key(query=query, embedding_model=embedding_model),
            value=_SearchEmbeddingPayload(embedding=embedding),
            ttl_seconds=self._ttl_seconds,
        )


def _stable_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
