"""
Abstract: Unit tests for root Unclassified taxonomy assignment backfill.
Out of scope: SQL execution, CLI wiring, and migration behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.taxonomy.dto import TaxonomyNodeRecord
from modules.taxonomy.root_unclassified_backfill import (
    TaxonomyRootUnclassifiedBackfillService,
)


@dataclass(slots=True)
class _StubRepo:
    total_nodes: int
    assignment_count: int
    missing_counts: list[int]
    root: TaxonomyNodeRecord | None = None
    root_unclassified: TaxonomyNodeRecord | None = None
    inserted_assignments: int = 0
    ensure_calls: int = 0
    bulk_assign_calls: list[int] = field(default_factory=list)
    committed: bool = False
    rolled_back: bool = False
    tree_nodes: list[TaxonomyNodeRecord] = field(default_factory=list)
    assigned_node_ids_by_leaf: dict[int, list[int]] = field(default_factory=dict)
    cleared_projection: bool = False
    projection_batches: list[tuple[int, list[int]]] = field(default_factory=list)

    async def get_root_node(self) -> TaxonomyNodeRecord | None:
        return self.root

    async def get_child_by_name(self, *, parent_id: int, name: str) -> TaxonomyNodeRecord | None:
        assert parent_id == 1
        assert name == "Unclassified"
        return self.root_unclassified

    async def ensure_root_with_unclassified(self) -> tuple[TaxonomyNodeRecord, TaxonomyNodeRecord]:
        self.ensure_calls += 1
        self.root = TaxonomyNodeRecord(
            id=1,
            parent_id=None,
            name="Root",
            route_slug="root",
            depth=0,
            is_leaf=False,
        )
        self.root_unclassified = TaxonomyNodeRecord(
            id=2,
            parent_id=1,
            name="Unclassified",
            route_slug="unclassified",
            depth=1,
            is_leaf=True,
        )
        return self.root, self.root_unclassified

    async def count_nodes(self) -> int:
        return self.total_nodes

    async def count_taxonomy_assignments(self) -> int:
        return self.assignment_count

    async def count_nodes_missing_taxonomy_assignment(self) -> int:
        return self.missing_counts.pop(0)

    async def assign_unassigned_nodes_to_leaf(self, *, leaf_id: int) -> None:
        self.bulk_assign_calls.append(leaf_id)

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def list_assigned_node_ids_for_leaf(self, *, leaf_id: int) -> list[int]:
        return list(self.assigned_node_ids_by_leaf.get(leaf_id, []))

    async def clear_all_projected_edge_ids(self) -> None:
        self.cleared_projection = True

    async def add_projected_edge_ids_for_leaf(self, *, leaf_id: int, edge_ids: list[int]) -> None:
        self.projection_batches.append((leaf_id, list(edge_ids)))

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@dataclass(slots=True)
class _StubProjectionPort:
    adjacent_edge_ids: list[int]
    requests: list[list[int]] = field(default_factory=list)

    async def list_adjacent_edge_ids_for_node_ids(self, *, node_ids: list[int]) -> list[int]:
        self.requests.append(list(node_ids))
        return list(self.adjacent_edge_ids)


@pytest.mark.anyio
async def test_dry_run_reports_missing_assignments_without_writes() -> None:
    repo = _StubRepo(
        total_nodes=10,
        assignment_count=0,
        missing_counts=[10],
    )
    service = TaxonomyRootUnclassifiedBackfillService(repo=repo)

    result = await service.run(apply=False)

    assert result.mode == "dry-run"
    assert result.root_id is None
    assert result.root_unclassified_id is None
    assert result.total_cards == 10
    assert result.assigned_before == 0
    assert result.missing_before == 10
    assert result.inserted_assignments == 0
    assert result.missing_after == 10
    assert result.projection_rebuilt is False
    assert repo.ensure_calls == 0
    assert repo.bulk_assign_calls == []
    assert repo.committed is False
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_apply_backfills_missing_assignments_and_rebuilds_projection() -> None:
    repo = _StubRepo(
        total_nodes=10,
        assignment_count=3,
        missing_counts=[7, 0],
        inserted_assignments=7,
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
                name="Unclassified",
                route_slug="unclassified",
                depth=1,
                is_leaf=True,
            ),
        ],
        assigned_node_ids_by_leaf={2: [11, 12]},
    )
    projection_port = _StubProjectionPort(adjacent_edge_ids=[101, 102])
    service = TaxonomyRootUnclassifiedBackfillService(
        repo=repo,
        knowledge_projection_port=projection_port,
    )

    result = await service.run(apply=True)

    assert result.mode == "apply"
    assert result.root_id == 1
    assert result.root_unclassified_id == 2
    assert result.total_cards == 10
    assert result.assigned_before == 3
    assert result.missing_before == 7
    assert result.inserted_assignments == 7
    assert result.missing_after == 0
    assert result.projection_rebuilt is True
    assert repo.ensure_calls == 1
    assert repo.bulk_assign_calls == [2]
    assert repo.cleared_projection is True
    assert projection_port.requests == [[11, 12]]
    assert repo.projection_batches == [(2, [101, 102])]
    assert repo.committed is True
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_apply_rolls_back_when_backfill_fails() -> None:
    class _FailingRepo(_StubRepo):
        async def assign_unassigned_nodes_to_leaf(self, *, leaf_id: int) -> None:
            raise RuntimeError("bulk assignment failed")

    repo = _FailingRepo(
        total_nodes=10,
        assignment_count=0,
        missing_counts=[10],
    )
    service = TaxonomyRootUnclassifiedBackfillService(repo=repo)

    with pytest.raises(RuntimeError, match="bulk assignment failed"):
        await service.run(apply=True)

    assert repo.committed is False
    assert repo.rolled_back is True
