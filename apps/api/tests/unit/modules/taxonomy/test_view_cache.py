"""
Abstract: Unit tests for taxonomy view Redis cache behavior.
Out of scope: Redis server integration and taxonomy service orchestration.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from modules.taxonomy.dto import (
    TaxonomyLeafLayout,
    TaxonomyLeafLayoutEdge,
    TaxonomyLeafLayoutNode,
    TaxonomyLeafWorldBounds,
)
from modules.taxonomy.view_cache import (
    TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS,
    TAXONOMY_VIEW_LEAF_LAYOUT_CACHE_TTL_SECONDS,
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


@pytest.mark.anyio
async def test_leaf_layout_cache_stores_and_reads_layout_payload() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)
    layout = TaxonomyLeafLayout(
        layout_version="taxonomy-leaf-layout-v2",
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        world_bounds=TaxonomyLeafWorldBounds(
            min_x=-5.0,
            min_y=-7.0,
            max_x=11.0,
            max_y=13.0,
        ),
        nodes=[
            TaxonomyLeafLayoutNode(id=11, scope="inner", x=1.5, y=2.5),
        ],
        edges=[
            TaxonomyLeafLayoutEdge(source_node_id=11, target_node_id=77, strength=0.42),
        ],
    )

    await cache.set_leaf_layout(leaf_id=9, layout=layout)
    cached = await cache.get_leaf_layout(leaf_id=9)

    assert cached == layout
    assert redis.set_calls[0][0] == "taxonomy:view:v1:leaf-layout:taxonomy-leaf-layout-v2:9"
    assert redis.set_calls[0][2] == TAXONOMY_VIEW_LEAF_LAYOUT_CACHE_TTL_SECONDS


@pytest.mark.anyio
async def test_leaf_layout_cache_rejects_malformed_payload() -> None:
    redis = _FakeRedis()
    redis.values["taxonomy:view:v1:leaf-layout:taxonomy-leaf-layout-v2:9"] = '{"nodes":"bad"}'
    cache = TaxonomyViewRedisCache(redis=redis)

    with pytest.raises(ValueError, match="leaf layout cache payload"):
        await cache.get_leaf_layout(leaf_id=9)


@pytest.mark.anyio
async def test_leaf_layout_lock_uses_per_leaf_single_flight_key() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)

    acquired = await cache.acquire_leaf_layout_lock(leaf_id=9)

    assert acquired is True
    assert redis.set_calls == [
        ("taxonomy:view:v1:leaf-layout:taxonomy-leaf-layout-v2:9:lock", "1", 30, True)
    ]
