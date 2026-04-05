"""
Abstract: Unit tests for taxonomy service tree assembly and assignment orchestration.
Out of scope: SQL query details, trigger enforcement, and HTTP transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord
from modules.taxonomy.service import TaxonomyService


@dataclass(slots=True)
class _StubRepo:
    tree_nodes: list[TaxonomyNodeRecord] = field(default_factory=list)
    children: list[TaxonomyNodeRecord] = field(default_factory=list)
    assignment: TaxonomyAssignmentRecord | None = None
    set_result: TaxonomyAssignmentRecord | None = None
    committed: bool = False
    rolled_back: bool = False
    fail_on_set: bool = False

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]:
        assert parent_id == 1
        return list(self.children)

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        assert node_id == 41
        return self.assignment

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
        assigned_at: datetime,
    ) -> TaxonomyAssignmentRecord:
        assert node_id == 41
        assert taxonomy_node_id == 9
        assert assigned_at == datetime(2026, 4, 5, 3, 0, tzinfo=UTC)
        if self.fail_on_set:
            raise RuntimeError("assignment write failed")
        assert self.set_result is not None
        return self.set_result

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def _leaf_assignment() -> TaxonomyAssignmentRecord:
    return TaxonomyAssignmentRecord(
        id=7,
        node_id=41,
        taxonomy_node=TaxonomyNodeRecord(
            id=9,
            parent_id=2,
            name="General",
            depth=2,
            is_leaf=True,
        ),
        assigned_at=datetime(2026, 4, 5, 3, 0, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_list_tree_builds_nested_nodes_from_repo_records() -> None:
    service = TaxonomyService(
        repo=_StubRepo(
            tree_nodes=[
                TaxonomyNodeRecord(id=1, parent_id=None, name="Science", depth=0, is_leaf=False),
                TaxonomyNodeRecord(id=2, parent_id=1, name="Mathematics", depth=1, is_leaf=False),
                TaxonomyNodeRecord(id=3, parent_id=2, name="Algebra", depth=2, is_leaf=True),
                TaxonomyNodeRecord(id=4, parent_id=1, name="Physics", depth=1, is_leaf=True),
            ]
        )
    )

    tree = await service.list_tree()

    assert [node.name for node in tree] == ["Science"]
    assert [node.name for node in tree[0].children] == ["Mathematics", "Physics"]
    assert [node.name for node in tree[0].children[0].children] == ["Algebra"]


@pytest.mark.anyio
async def test_list_children_returns_repo_ordered_children() -> None:
    service = TaxonomyService(
        repo=_StubRepo(
            children=[
                TaxonomyNodeRecord(id=5, parent_id=1, name="Chemistry", depth=1, is_leaf=True),
                TaxonomyNodeRecord(id=6, parent_id=1, name="Physics", depth=1, is_leaf=True),
            ]
        )
    )

    children = await service.list_children(parent_id=1)

    assert [child.name for child in children] == ["Chemistry", "Physics"]


@pytest.mark.anyio
async def test_get_assignment_for_node_returns_leaf_assignment() -> None:
    service = TaxonomyService(repo=_StubRepo(assignment=_leaf_assignment()))

    assignment = await service.get_assignment_for_node(node_id=41)

    assert assignment is not None
    assert assignment.taxonomy_node.name == "General"


@pytest.mark.anyio
async def test_set_final_assignment_commits_written_assignment() -> None:
    repo = _StubRepo(set_result=_leaf_assignment())
    service = TaxonomyService(repo=repo)

    assignment = await service.set_final_assignment(
        node_id=41,
        taxonomy_node_id=9,
        assigned_at=datetime(2026, 4, 5, 3, 0, tzinfo=UTC),
    )

    assert assignment.taxonomy_node.id == 9
    assert repo.committed is True
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_set_final_assignment_rolls_back_and_reraises() -> None:
    repo = _StubRepo(fail_on_set=True)
    service = TaxonomyService(repo=repo)

    with pytest.raises(RuntimeError, match="assignment write failed"):
        await service.set_final_assignment(
            node_id=41,
            taxonomy_node_id=9,
            assigned_at=datetime(2026, 4, 5, 3, 0, tzinfo=UTC),
        )

    assert repo.committed is False
    assert repo.rolled_back is True
