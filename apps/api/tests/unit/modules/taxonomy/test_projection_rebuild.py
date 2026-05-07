"""
Abstract: Unit tests for taxonomy card-scope projection rebuild orchestration.
Out of scope: CLI wiring, migration execution, and SQL statement details.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.taxonomy.dto import TaxonomyAssignmentCount, TaxonomyNodeRecord, TaxonomyScopeIdentity
from modules.taxonomy.projection_rebuild import rebuild_taxonomy_scope_projection_edges
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND


@dataclass(slots=True)
class _StubRepo:
    tree_nodes: list[TaxonomyNodeRecord]
    assignment_counts: list[TaxonomyAssignmentCount]
    assigned_node_ids_by_scope: dict[tuple[str, int], list[int]]
    cleared: bool = False
    add_calls: list[tuple[TaxonomyScopeIdentity, list[int]]] = field(default_factory=list)

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def list_assignment_counts(self) -> list[TaxonomyAssignmentCount]:
        return list(self.assignment_counts)

    async def list_assigned_node_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]:
        return list(
            self.assigned_node_ids_by_scope.get(
                (scope_identity.scope_kind, scope_identity.taxonomy_node_id),
                [],
            )
        )

    async def clear_all_projected_edge_ids(self) -> None:
        self.cleared = True

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None:
        self.add_calls.append((scope_identity, list(edge_ids)))


@dataclass(slots=True)
class _StubProjectionPort:
    edge_ids_by_node_tuple: dict[tuple[int, ...], list[int]]
    adjacent_requests: list[list[int]] = field(default_factory=list)

    async def list_adjacent_edge_ids_for_node_ids(self, *, node_ids: list[int]) -> list[int]:
        self.adjacent_requests.append(list(node_ids))
        return list(self.edge_ids_by_node_tuple.get(tuple(node_ids), []))


@pytest.mark.anyio
async def test_rebuild_scope_projection_edges_repopulates_active_scope_rows() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(
                id=1,
                parent_id=None,
                name="Root",
                route_slug="root",
                depth=0,
            ),
            TaxonomyNodeRecord(
                id=2,
                parent_id=1,
                name="Leaf A",
                route_slug="leaf-a",
                depth=1,
            ),
            TaxonomyNodeRecord(
                id=3,
                parent_id=1,
                name="Leaf B",
                route_slug="leaf-b",
                depth=1,
            ),
        ],
        assignment_counts=[
            TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=2),
        ],
        assigned_node_ids_by_scope={
            (TAXONOMY_NODE_SCOPE_KIND, 2): [11, 12],
        },
    )
    projection_port = _StubProjectionPort(
        edge_ids_by_node_tuple={
            (11, 12): [501, 502],
            (): [],
        }
    )
    await rebuild_taxonomy_scope_projection_edges(
        repo=repo,
        projection_port=projection_port,
    )

    assert repo.cleared is True
    assert projection_port.adjacent_requests == [[11, 12]]
    assert repo.add_calls == [
        (
            TaxonomyScopeIdentity(scope_kind=TAXONOMY_NODE_SCOPE_KIND, taxonomy_node_id=2),
            [501, 502],
        ),
    ]


@pytest.mark.anyio
async def test_rebuild_scope_projection_edges_excludes_hidden_backlog_assignments() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", route_slug="root", depth=0),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Science", route_slug="science", depth=1),
            TaxonomyNodeRecord(id=3, parent_id=2, name="Heat", route_slug="heat", depth=2),
            TaxonomyNodeRecord(id=4, parent_id=1, name="Math", route_slug="math", depth=1),
        ],
        assignment_counts=[
            TaxonomyAssignmentCount(taxonomy_node_id=1, card_count=2),
            TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=3),
            TaxonomyAssignmentCount(taxonomy_node_id=3, card_count=5),
            TaxonomyAssignmentCount(taxonomy_node_id=4, card_count=7),
        ],
        assigned_node_ids_by_scope={
            (TAXONOMY_NODE_SCOPE_KIND, 3): [31, 32],
            (TAXONOMY_NODE_SCOPE_KIND, 4): [41],
        },
    )
    projection_port = _StubProjectionPort(
        edge_ids_by_node_tuple={
            (31, 32): [601],
            (41,): [701],
        }
    )

    await rebuild_taxonomy_scope_projection_edges(
        repo=repo,
        projection_port=projection_port,
    )

    assert projection_port.adjacent_requests == [[41], [31, 32]]
    assert repo.add_calls == [
        (
            TaxonomyScopeIdentity(scope_kind=TAXONOMY_NODE_SCOPE_KIND, taxonomy_node_id=4),
            [701],
        ),
        (
            TaxonomyScopeIdentity(scope_kind=TAXONOMY_NODE_SCOPE_KIND, taxonomy_node_id=3),
            [601],
        ),
    ]
