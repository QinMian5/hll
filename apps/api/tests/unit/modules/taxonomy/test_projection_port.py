"""
Abstract: Unit tests for taxonomy projection cache invalidation adapter behavior.
Out of scope: SQL repository behavior and Redis cache serialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.taxonomy.projection_port import CacheInvalidatingTaxonomyProjectionPort


@dataclass(slots=True)
class _StubProjectionRepo:
    assigned_leaf_id: int = 9
    add_calls: list[tuple[int, list[int]]] = field(default_factory=list)
    assigned_node_ids: list[int] = field(default_factory=list)
    leaf_lookup_by_node_id: dict[int, int] = field(default_factory=lambda: {11: 9, 12: 4})

    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int:
        self.assigned_node_ids.append(node_id)
        return self.assigned_leaf_id

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        return {
            node_id: self.leaf_lookup_by_node_id[node_id]
            for node_id in node_ids
            if node_id in self.leaf_lookup_by_node_id
        }

    async def add_projected_edge_ids_for_leaf(self, *, leaf_id: int, edge_ids: list[int]) -> None:
        self.add_calls.append((leaf_id, list(edge_ids)))


@dataclass(slots=True)
class _StubViewCache:
    invalidated_leaf_ids: list[int] = field(default_factory=list)

    async def invalidate_leaf_layout(self, *, leaf_id: int) -> None:
        self.invalidated_leaf_ids.append(leaf_id)


@pytest.mark.anyio
async def test_assignment_to_root_unclassified_invalidates_assigned_leaf_layout() -> None:
    repo = _StubProjectionRepo(assigned_leaf_id=9)
    cache = _StubViewCache()
    port = CacheInvalidatingTaxonomyProjectionPort(repo=repo, view_cache=cache)

    leaf_id = await port.assign_node_to_root_unclassified(node_id=41)

    assert leaf_id == 9
    assert repo.assigned_node_ids == [41]
    assert cache.invalidated_leaf_ids == [9]


@pytest.mark.anyio
async def test_projected_edge_insert_invalidates_target_leaf_layout() -> None:
    repo = _StubProjectionRepo()
    cache = _StubViewCache()
    port = CacheInvalidatingTaxonomyProjectionPort(repo=repo, view_cache=cache)

    await port.add_projected_edge_ids_for_leaf(leaf_id=4, edge_ids=[501, 502])

    assert repo.add_calls == [(4, [501, 502])]
    assert cache.invalidated_leaf_ids == [4]


@pytest.mark.anyio
async def test_leaf_lookup_delegates_without_invalidating_layout() -> None:
    repo = _StubProjectionRepo()
    cache = _StubViewCache()
    port = CacheInvalidatingTaxonomyProjectionPort(repo=repo, view_cache=cache)

    result = await port.list_leaf_ids_for_node_ids(node_ids=[12, 99, 11])

    assert result == {12: 4, 11: 9}
    assert cache.invalidated_leaf_ids == []
