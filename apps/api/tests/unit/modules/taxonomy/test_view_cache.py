"""
Abstract: Unit tests for taxonomy view Redis cache behavior.
Out of scope: Redis server integration and taxonomy service orchestration.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from modules.taxonomy.dto import (
    TaxonomyCardScopeLayout,
    TaxonomyCardScopeLayoutEdge,
    TaxonomyCardScopeLayoutNode,
    TaxonomyCardScopeWorldBounds,
    TaxonomyScopeIdentity,
)
from modules.taxonomy.schema import (
    TaxonomyCardScopeWorldBoundsResponse,
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeCardScopeViewResponse,
    TaxonomyRootViewResponse,
    TaxonomyViewChildResponse,
    TaxonomyViewScopeResponse,
)
from modules.taxonomy.view_cache import (
    TAXONOMY_VIEW_CARD_SCOPE_LAYOUT_CACHE_TTL_SECONDS,
    TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS,
    TAXONOMY_VIEW_RESPONSE_CACHE_TTL_SECONDS,
    TaxonomyViewRedisCache,
)


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.delete_calls: list[str] = []
        self.set_calls: list[tuple[str, str, int | None, bool | None]] = []
        self.rpush_calls: list[tuple[str, str]] = []
        self.lpop_calls: list[str] = []

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def delete(self, key: str) -> int:
        self.delete_calls.append(key)
        existed = key in self.values
        self.values.pop(key, None)
        return int(existed)

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

    async def rpush(self, key: str, value: str) -> int:
        self.rpush_calls.append((key, value))
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])

    async def lpop(self, key: str) -> str | None:
        self.lpop_calls.append(key)
        values = self.lists.get(key, [])
        if not values:
            return None
        return values.pop(0)


def _view_scope(
    *,
    id: int,
    parent_id: int | None,
    name: str,
    scope_kind: str = "taxonomy_node",
) -> TaxonomyViewScopeResponse:
    route_path = "" if parent_id is None else name.lower()
    return TaxonomyViewScopeResponse(
        scope_kind=scope_kind,
        taxonomy_node_id=id,
        parent_taxonomy_node_id=parent_id,
        name=name,
        route_slug=name.lower(),
        route_path=route_path,
        depth=0 if parent_id is None else 1,
    )


def _root_view() -> TaxonomyRootViewResponse:
    return TaxonomyRootViewResponse(
        breadcrumb=[],
        children=[
            TaxonomyViewChildResponse(
                scope_kind="taxonomy_node",
                taxonomy_node_id=2,
                parent_taxonomy_node_id=1,
                name="Science",
                route_slug="science",
                route_path="science",
                depth=1,
                node_kind="branch",
                descendant_card_count=3,
            )
        ],
    )


def _branch_view() -> TaxonomyNodeBranchViewResponse:
    return TaxonomyNodeBranchViewResponse(
        node_kind="branch",
        current_scope=_view_scope(id=2, parent_id=1, name="Science"),
        breadcrumb=[
            _view_scope(id=1, parent_id=None, name="Root"),
            _view_scope(id=2, parent_id=1, name="Science"),
        ],
        children=[],
    )


def _card_scope_metadata_view() -> TaxonomyNodeCardScopeViewResponse:
    return TaxonomyNodeCardScopeViewResponse(
        node_kind="card_scope",
        current_scope=_view_scope(id=3, parent_id=1, name="Cards"),
        breadcrumb=[
            _view_scope(id=1, parent_id=None, name="Root"),
            _view_scope(id=3, parent_id=1, name="Cards"),
        ],
        layout_version="taxonomy-card-scope-layout-v1",
        world_bounds=TaxonomyCardScopeWorldBoundsResponse(
            min_x=-1.0,
            min_y=-2.0,
            max_x=3.0,
            max_y=4.0,
        ),
        node_count=3,
        edge_count=2,
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_root_view_response_cache_stores_and_reads_validated_payload() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis, view_response_ttl_seconds=45)
    root_view = _root_view()

    await cache.set_root_view(root_view)
    cached = await cache.get_root_view()

    assert cached == root_view
    assert redis.set_calls[0][0] == "knowledge:api:taxonomy-view:v1:root"
    assert redis.set_calls[0][2] == 45


@pytest.mark.anyio
async def test_node_view_response_cache_supports_branch_and_card_scope_payloads() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)
    branch_view = _branch_view()
    card_scope_view = _card_scope_metadata_view()

    await cache.set_node_view(node_id=2, view=branch_view)
    await cache.set_node_view(node_id=3, view=card_scope_view)

    assert await cache.get_node_view(node_id=2) == branch_view
    assert await cache.get_node_view(node_id=3) == card_scope_view
    assert redis.set_calls[0][0] == "knowledge:api:taxonomy-view:v1:node:2"
    assert redis.set_calls[1][0] == "knowledge:api:taxonomy-view:v1:node:3"
    assert redis.set_calls[0][2] == TAXONOMY_VIEW_RESPONSE_CACHE_TTL_SECONDS


@pytest.mark.anyio
async def test_path_view_response_cache_uses_hashed_route_path_key() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)
    branch_view = _branch_view()

    await cache.set_path_view(route_path="science/mathematics", view=branch_view)
    cached = await cache.get_path_view(route_path="science/mathematics")

    assert cached == branch_view
    assert redis.set_calls[0][0].startswith("knowledge:api:taxonomy-view:v1:path:")
    assert "science/mathematics" not in redis.set_calls[0][0]


@pytest.mark.anyio
async def test_taxonomy_response_cache_rejects_malformed_payload() -> None:
    redis = _FakeRedis()
    redis.values["knowledge:api:taxonomy-view:v1:root"] = "{}"
    cache = TaxonomyViewRedisCache(redis=redis)

    with pytest.raises(ValueError, match="root view cache payload"):
        await cache.get_root_view()


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
async def test_card_scope_layout_cache_stores_and_reads_layout_payload() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)
    scope_identity = TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=9)
    layout = TaxonomyCardScopeLayout(
        layout_version="taxonomy-card-scope-layout-v1",
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        world_bounds=TaxonomyCardScopeWorldBounds(
            min_x=-5.0,
            min_y=-7.0,
            max_x=11.0,
            max_y=13.0,
        ),
        nodes=[
            TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=1.5, y=2.5),
        ],
        edges=[
            TaxonomyCardScopeLayoutEdge(source_node_id=11, target_node_id=77, strength=0.42),
        ],
    )

    await cache.set_card_scope_layout(scope_identity=scope_identity, layout=layout)
    cached = await cache.get_card_scope_layout(scope_identity=scope_identity)

    assert cached == layout
    assert (
        redis.set_calls[0][0]
        == "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9"
    )
    assert redis.set_calls[0][2] == TAXONOMY_VIEW_CARD_SCOPE_LAYOUT_CACHE_TTL_SECONDS


@pytest.mark.anyio
async def test_card_scope_layout_cache_rejects_malformed_payload() -> None:
    redis = _FakeRedis()
    scope_identity = TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=9)
    redis.values[
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9"
    ] = '{"nodes":"bad"}'
    cache = TaxonomyViewRedisCache(redis=redis)

    with pytest.raises(ValueError, match="card-scope layout cache payload"):
        await cache.get_card_scope_layout(scope_identity=scope_identity)


@pytest.mark.anyio
async def test_card_scope_layout_lock_uses_per_scope_single_flight_key() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)
    scope_identity = TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=9)

    acquired = await cache.acquire_card_scope_layout_lock(scope_identity=scope_identity)

    assert acquired is True
    assert redis.set_calls == [
        (
            "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:"
            "taxonomy_node:9:lock",
            "1",
            30,
            True,
        )
    ]


@pytest.mark.anyio
async def test_card_scope_layout_compute_request_enqueues_each_scope_once() -> None:
    redis = _FakeRedis()
    cache = TaxonomyViewRedisCache(redis=redis)
    scope_identity = TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=9)

    first_requested = await cache.request_card_scope_layout_compute(scope_identity=scope_identity)
    second_requested = await cache.request_card_scope_layout_compute(scope_identity=scope_identity)

    assert first_requested is True
    assert second_requested is False
    assert redis.rpush_calls == [
        (
            "taxonomy:view:v1:card-scope-layout:requests",
            '{"scope_kind":"taxonomy_node","taxonomy_node_id":9}',
        )
    ]
    assert (
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:pending",
        "1",
        600,
        True,
    ) in redis.set_calls


@pytest.mark.anyio
async def test_card_scope_layout_compute_request_skips_running_scope() -> None:
    redis = _FakeRedis()
    scope_identity = TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=9)
    redis.values[
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:running"
    ] = "1"
    cache = TaxonomyViewRedisCache(redis=redis)

    requested = await cache.request_card_scope_layout_compute(scope_identity=scope_identity)

    assert requested is False
    assert redis.rpush_calls == []


@pytest.mark.anyio
async def test_card_scope_layout_compute_claim_marks_scope_running_and_clears_pending() -> None:
    redis = _FakeRedis()
    redis.lists["taxonomy:view:v1:card-scope-layout:requests"] = [
        '{"scope_kind":"taxonomy_node","taxonomy_node_id":9}'
    ]
    cache = TaxonomyViewRedisCache(redis=redis)

    scope_identity = await cache.claim_card_scope_layout_compute()

    assert scope_identity == TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=9)
    assert (
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:running",
        "1",
        1800,
        True,
    ) in redis.set_calls
    assert (
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:pending"
        in redis.delete_calls
    )


@pytest.mark.anyio
async def test_card_scope_layout_compute_completion_clears_singleflight_state() -> None:
    redis = _FakeRedis()
    scope_identity = TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=9)
    redis.values[
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:pending"
    ] = "1"
    redis.values[
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:running"
    ] = "1"
    cache = TaxonomyViewRedisCache(redis=redis)

    await cache.complete_card_scope_layout_compute(scope_identity=scope_identity)

    assert (
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:pending"
        in redis.delete_calls
    )
    assert (
        "taxonomy:view:v1:card-scope-layout:taxonomy-card-scope-layout-v1:taxonomy_node:9:running"
        in redis.delete_calls
    )


@pytest.mark.anyio
async def test_card_scope_layout_cache_does_not_expose_write_path_invalidation_api() -> None:
    cache = TaxonomyViewRedisCache(redis=_FakeRedis())

    assert not hasattr(cache, "invalidate_card_scope_layout")
