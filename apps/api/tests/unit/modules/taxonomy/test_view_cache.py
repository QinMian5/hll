"""
Abstract: Unit tests for taxonomy view Redis cache behavior.
Out of scope: Redis server integration and taxonomy service orchestration.
"""

from __future__ import annotations

import pytest

from modules.taxonomy.view_cache import (
    TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS,
    TaxonomyViewRedisCache,
)


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
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True


@pytest.mark.anyio
async def test_descendant_counts_cache_reads_versioned_json_payload() -> None:
    redis = _FakeRedis()
    redis.values["taxonomy:view:v1:descendant-counts"] = '{"counts":{"1":3,"2":3,"9":0}}'
    cache = TaxonomyViewRedisCache(redis=redis)

    counts = await cache.get_descendant_counts()

    assert counts == {1: 3, 2: 3, 9: 0}


@pytest.mark.anyio
async def test_descendant_counts_cache_stores_json_with_ttl() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)

    await cache.set_descendant_counts({2: 4, 1: 4})

    assert redis.set_calls == [
        (
            "taxonomy:view:v1:descendant-counts",
            '{"counts":{"1":4,"2":4}}',
            TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS,
            None,
        )
    ]


@pytest.mark.anyio
async def test_descendant_counts_cache_rejects_malformed_payload() -> None:
    redis = _FakeRedis()
    redis.values["taxonomy:view:v1:descendant-counts"] = '{"counts":[1,2]}'
    cache = TaxonomyViewRedisCache(redis=redis)

    with pytest.raises(ValueError, match="descendant count cache payload"):
        await cache.get_descendant_counts()


@pytest.mark.anyio
async def test_descendant_counts_lock_uses_single_flight_key() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)

    acquired = await cache.acquire_descendant_counts_lock()

    assert acquired is True
    assert redis.set_calls == [("taxonomy:view:v1:descendant-counts:lock", "1", 30, True)]
