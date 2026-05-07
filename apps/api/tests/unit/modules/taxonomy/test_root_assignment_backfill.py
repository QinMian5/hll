"""
Abstract: Unit tests for root taxonomy assignment backfill.
Out of scope: SQL execution, CLI wiring, and migration behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.taxonomy.dto import TaxonomyAssignmentCount, TaxonomyNodeRecord, TaxonomyScopeIdentity
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND
from modules.taxonomy.root_assignment_backfill import TaxonomyRootAssignmentBackfillService


@dataclass(slots=True)
class _StubRepo:
    total_nodes: int
    assignment_count: int
    missing_counts: list[int]
    root: TaxonomyNodeRecord | None = None
    ensure_calls: int = 0
    bulk_assign_calls: list[int] = field(default_factory=list)
    committed: bool = False
    rolled_back: bool = False
    tree_nodes: list[TaxonomyNodeRecord] = field(default_factory=list)
    assignment_counts: list[TaxonomyAssignmentCount] = field(default_factory=list)
    assigned_node_ids_by_scope: dict[tuple[str, int], list[int]] = field(default_factory=dict)
    cleared_projection: bool = False
    projection_batches: list[tuple[TaxonomyScopeIdentity, list[int]]] = field(
        default_factory=list
    )

    async def get_root_node(self) -> TaxonomyNodeRecord | None:
        return self.root

    async def ensure_root(self) -> TaxonomyNodeRecord:
        self.ensure_calls += 1
        self.root = TaxonomyNodeRecord(
            id=1,
            parent_id=None,
            name="Root",
            route_slug="root",
            depth=0,
        )
        return self.root

    async def count_nodes(self) -> int:
        return self.total_nodes

    async def count_taxonomy_assignments(self) -> int:
        return self.assignment_count

    async def count_nodes_missing_taxonomy_assignment(self) -> int:
        return self.missing_counts.pop(0)

    async def assign_unassigned_nodes_to_taxonomy_node(self, *, taxonomy_node_id: int) -> None:
        self.bulk_assign_calls.append(taxonomy_node_id)

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
        self.cleared_projection = True

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None:
        self.projection_batches.append((scope_identity, list(edge_ids)))

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
    service = TaxonomyRootAssignmentBackfillService(repo=repo)

    result = await service.run(apply=False)

    assert result.mode == "dry-run"
    assert result.root_id is None
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
        tree_nodes=[
            TaxonomyNodeRecord(
                id=1,
                parent_id=None,
                name="Root",
                route_slug="root",
                depth=0,
            ),
        ],
        assignment_counts=[
            TaxonomyAssignmentCount(taxonomy_node_id=1, card_count=7),
        ],
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 1): [11, 12]},
    )
    projection_port = _StubProjectionPort(adjacent_edge_ids=[101, 102])
    service = TaxonomyRootAssignmentBackfillService(
        repo=repo,
        knowledge_projection_port=projection_port,
    )

    result = await service.run(apply=True)

    assert result.mode == "apply"
    assert result.root_id == 1
    assert result.total_cards == 10
    assert result.assigned_before == 3
    assert result.missing_before == 7
    assert result.inserted_assignments == 7
    assert result.missing_after == 0
    assert result.projection_rebuilt is True
    assert repo.ensure_calls == 1
    assert repo.bulk_assign_calls == [1]
    assert repo.cleared_projection is True
    assert projection_port.requests == []
    assert repo.projection_batches == []
    assert repo.committed is True
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_apply_rolls_back_when_backfill_fails() -> None:
    class _FailingRepo(_StubRepo):
        async def assign_unassigned_nodes_to_taxonomy_node(
            self,
            *,
            taxonomy_node_id: int,
        ) -> None:
            raise RuntimeError("bulk assignment failed")

    repo = _FailingRepo(
        total_nodes=10,
        assignment_count=0,
        missing_counts=[10],
    )
    service = TaxonomyRootAssignmentBackfillService(repo=repo)

    with pytest.raises(RuntimeError, match="bulk assignment failed"):
        await service.run(apply=True)

    assert repo.committed is False
    assert repo.rolled_back is True
