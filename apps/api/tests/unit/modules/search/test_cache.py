"""
Abstract: Unit tests for Search Redis cache keys and payload adapters.
Out of scope: Search ranking behavior and Redis server integration.
"""

from __future__ import annotations

import pytest

from modules.search.cache import (
    SEARCH_ALGORITHM_VERSION,
    SEARCH_EMBEDDING_CACHE_SCHEMA_VERSION,
    SEARCH_RESPONSE_CACHE_SCHEMA_VERSION,
    SearchRedisEmbeddingCache,
    SearchRedisResponseCache,
    normalize_search_query,
    search_embedding_cache_key,
    search_response_cache_key,
)
from modules.search.schema import MatchedCardResponse, SearchResponse


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, int | None, bool | None]] = []

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool | None = None,
    ) -> bool:
        self.set_calls.append((key, value, ex, nx))
        self.values[key] = value
        return True


def _search_response() -> SearchResponse:
    return SearchResponse(
        matched_cards=[
            MatchedCardResponse(
                node_id=11,
                current_version=2,
                title="Alpha",
                content="alpha content",
            )
        ],
        connected_titles=["Beta"],
    )


def test_normalize_search_query_collapses_whitespace_and_case_folds() -> None:
    assert normalize_search_query("  Mixed\tCASE\nQuery  ") == "mixed case query"


def test_search_response_cache_key_uses_normalized_hashed_inputs() -> None:
    first = search_response_cache_key(
        query="  Graph  VIEW ",
        max_matched=3,
        max_connected=5,
    )
    second = search_response_cache_key(
        query="graph view",
        max_matched=3,
        max_connected=5,
    )
    changed_limit = search_response_cache_key(
        query="graph view",
        max_matched=4,
        max_connected=5,
    )

    assert first == second
    assert first != changed_limit
    assert first.startswith(
        f"knowledge:api:search-response:{SEARCH_RESPONSE_CACHE_SCHEMA_VERSION}:"
    )
    assert "graph view" not in first
    assert SEARCH_ALGORITHM_VERSION not in first


def test_search_embedding_cache_key_uses_model_and_normalized_query_hash() -> None:
    first = search_embedding_cache_key(
        query="  Graph  VIEW ",
        embedding_model="text-embedding-3-small",
    )
    second = search_embedding_cache_key(
        query="graph view",
        embedding_model="text-embedding-3-small",
    )
    changed_model = search_embedding_cache_key(
        query="graph view",
        embedding_model="text-embedding-3-large",
    )

    assert first == second
    assert first != changed_model
    assert first.startswith(
        "knowledge:api:search-embedding:"
        f"{SEARCH_EMBEDDING_CACHE_SCHEMA_VERSION}:text-embedding-3-small:"
    )
    assert "graph view" not in first


@pytest.mark.anyio
async def test_search_response_cache_stores_and_reads_validated_payload() -> None:
    redis = _FakeRedis()
    cache = SearchRedisResponseCache(redis=redis, ttl_seconds=60)
    response = _search_response()

    await cache.set(
        query="Graph View",
        max_matched=3,
        max_connected=5,
        response=response,
    )
    cached = await cache.get(query="graph view", max_matched=3, max_connected=5)

    assert cached == response
    assert redis.set_calls[0][2] == 60


@pytest.mark.anyio
async def test_search_embedding_cache_stores_and_reads_vector_payload() -> None:
    redis = _FakeRedis()
    cache = SearchRedisEmbeddingCache(redis=redis, ttl_seconds=86400)

    await cache.set(
        query="Graph View",
        embedding_model="text-embedding-3-small",
        embedding=[0.1, 0.2, 0.3],
    )
    cached = await cache.get(query="graph view", embedding_model="text-embedding-3-small")

    assert cached == [0.1, 0.2, 0.3]
    assert redis.set_calls[0][2] == 86400
