"""
Abstract: Unit tests for taxonomy leaf projection rebuild orchestration.
Out of scope: CLI wiring, migration execution, and SQL statement details.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.taxonomy.dto import TaxonomyNodeRecord
from modules.taxonomy.projection_rebuild import rebuild_taxonomy_leaf_projection_edges


@dataclass(slots=True)
class _StubRepo:
    tree_nodes: list[TaxonomyNodeRecord]
    assigned_node_ids_by_leaf: dict[int, list[int]]
    cleared: bool = False
    add_calls: list[tuple[int, list[int]]] = field(default_factory=list)

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def list_assigned_node_ids_for_leaf(self, *, leaf_id: int) -> list[int]:
        return list(self.assigned_node_ids_by_leaf.get(leaf_id, []))

    async def clear_all_projected_edge_ids(self) -> None:
        self.cleared = True

    async def add_projected_edge_ids_for_leaf(self, *, leaf_id: int, edge_ids: list[int]) -> None:
        self.add_calls.append((leaf_id, list(edge_ids)))


@dataclass(slots=True)
class _StubProjectionPort:
    edge_ids_by_node_tuple: dict[tuple[int, ...], list[int]]
    adjacent_requests: list[list[int]] = field(default_factory=list)

    async def list_adjacent_edge_ids_for_node_ids(self, *, node_ids: list[int]) -> list[int]:
        self.adjacent_requests.append(list(node_ids))
        return list(self.edge_ids_by_node_tuple.get(tuple(node_ids), []))


@dataclass(slots=True)
class _StubViewCache:
    invalidated_leaf_ids: list[int] = field(default_factory=list)

    async def invalidate_leaf_layout(self, *, leaf_id: int) -> None:
        self.invalidated_leaf_ids.append(leaf_id)


@pytest.mark.anyio
async def test_rebuild_taxonomy_leaf_projection_edges_clears_then_repopulates_all_leaf_rows() -> (
    None
):
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(
                id=1,
                parent_id=None,
                name="Root",
                route_slug="root",
                depth=0,
                is_leaf=False,
            ),
            TaxonomyNodeRecord(
                id=2,
                parent_id=1,
                name="Leaf A",
                route_slug="leaf-a",
                depth=1,
                is_leaf=True,
            ),
            TaxonomyNodeRecord(
                id=3,
                parent_id=1,
                name="Leaf B",
                route_slug="leaf-b",
                depth=1,
                is_leaf=True,
            ),
        ],
        assigned_node_ids_by_leaf={
            2: [11, 12],
            3: [],
        },
    )
    projection_port = _StubProjectionPort(
        edge_ids_by_node_tuple={
            (11, 12): [501, 502],
            (): [],
        }
    )

    cache = _StubViewCache()

    await rebuild_taxonomy_leaf_projection_edges(
        repo=repo,
        projection_port=projection_port,
        view_cache=cache,
    )

    assert repo.cleared is True
    assert projection_port.adjacent_requests == [[11, 12], []]
    assert repo.add_calls == [
        (2, [501, 502]),
        (3, []),
    ]
    assert cache.invalidated_leaf_ids == [2, 3]
