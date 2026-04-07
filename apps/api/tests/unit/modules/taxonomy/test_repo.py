"""
Abstract: Unit tests for taxonomy repository boundary behavior.
Out of scope: Database I/O, trigger enforcement, and service orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from modules.taxonomy.errors import TaxonomyAssignmentAlreadyExistsError
from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode
from modules.taxonomy.repo import TaxonomyRepo


class _StubScalarResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return list(self._values)


class _StubExecuteResult:
    def __init__(
        self,
        row: tuple[object, object] | None = None,
        rows: list[object] | None = None,
    ) -> None:
        self._row = row
        self._rows = rows if rows is not None else []

    def one_or_none(self) -> tuple[object, object] | None:
        return self._row

    def all(self) -> list[object]:
        return list(self._rows)


@dataclass(slots=True)
class _StubSession:
    scalars_results: list[_StubScalarResult] = field(default_factory=list)
    scalar_results: list[object | None] = field(default_factory=list)
    execute_results: list[_StubExecuteResult] = field(default_factory=list)
    added: list[object] = field(default_factory=list)
    flushed: bool = False

    async def scalars(self, statement: object) -> _StubScalarResult:
        assert statement is not None
        return self.scalars_results.pop(0)

    async def scalar(self, statement: object) -> object | None:
        assert statement is not None
        return self.scalar_results.pop(0)

    async def execute(self, statement: object) -> _StubExecuteResult:
        assert statement is not None
        return self.execute_results.pop(0)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.anyio
async def test_list_tree_nodes_returns_record_models() -> None:
    session = _StubSession(
        scalars_results=[
            _StubScalarResult(
                [
                    TaxonomyNode(id=1, parent_id=None, name="Science", depth=0, is_leaf=False),
                    TaxonomyNode(id=2, parent_id=1, name="Physics", depth=1, is_leaf=True),
                ]
            )
        ]
    )
    repo = TaxonomyRepo(session=session)

    records = await repo.list_tree_nodes()

    assert [record.model_dump() for record in records] == [
        {"id": 1, "parent_id": None, "name": "Science", "depth": 0, "is_leaf": False},
        {"id": 2, "parent_id": 1, "name": "Physics", "depth": 1, "is_leaf": True},
    ]


@pytest.mark.anyio
async def test_get_assignment_for_node_returns_leaf_assignment_details() -> None:
    assigned_at = datetime(2026, 4, 5, 1, 15, tzinfo=UTC)
    session = _StubSession(
        execute_results=[
            _StubExecuteResult(
                (
                    NodeTaxonomyAssignment(
                        id=9,
                        node_id=12,
                        taxonomy_node_id=4,
                        assigned_at=assigned_at,
                    ),
                    TaxonomyNode(
                        id=4,
                        parent_id=2,
                        name="Algebra",
                        depth=2,
                        is_leaf=True,
                    ),
                )
            )
        ]
    )
    repo = TaxonomyRepo(session=session)

    assignment = await repo.get_assignment_for_node(node_id=12)

    assert assignment is not None
    assert assignment.node_id == 12
    assert assignment.taxonomy_node.name == "Algebra"
    assert assignment.assigned_at == assigned_at


@pytest.mark.anyio
async def test_set_final_assignment_raises_when_assignment_already_exists() -> None:
    existing_assignment = NodeTaxonomyAssignment(
        id=7,
        node_id=99,
        taxonomy_node_id=3,
        assigned_at=datetime(2026, 4, 5, 1, 0, tzinfo=UTC),
    )
    session = _StubSession(
        scalar_results=[existing_assignment],
    )
    repo = TaxonomyRepo(session=session)

    with pytest.raises(TaxonomyAssignmentAlreadyExistsError):
        await repo.set_final_assignment(
            node_id=99,
            taxonomy_node_id=8,
        )

    assert existing_assignment.taxonomy_node_id == 3
    assert session.flushed is False


@pytest.mark.anyio
async def test_set_final_assignment_creates_when_assignment_missing() -> None:
    assigned_at = datetime(2026, 4, 5, 2, 30, tzinfo=UTC)
    persisted_assignment = NodeTaxonomyAssignment(
        id=17,
        node_id=99,
        taxonomy_node_id=8,
        assigned_at=assigned_at,
    )
    session = _StubSession(
        scalar_results=[None],
        execute_results=[
            _StubExecuteResult(
                (
                    persisted_assignment,
                    TaxonomyNode(
                        id=8,
                        parent_id=3,
                        name="General",
                        depth=2,
                        is_leaf=True,
                    ),
                )
            )
        ],
    )
    repo = TaxonomyRepo(session=session)

    assignment = await repo.set_final_assignment(
        node_id=99,
        taxonomy_node_id=8,
    )

    created_assignment = session.added[0]
    assert isinstance(created_assignment, NodeTaxonomyAssignment)
    assert created_assignment.assigned_at is None
    assert assignment.taxonomy_node.id == 8
    assert session.flushed is True


@pytest.mark.anyio
async def test_list_final_assignments_returns_leaf_assignments() -> None:
    class _AssignmentRow:
        def __init__(self, node_id: int, taxonomy_leaf_id: int) -> None:
            self.node_id = node_id
            self.taxonomy_leaf_id = taxonomy_leaf_id

    session = _StubSession(
        execute_results=[_StubExecuteResult(rows=[_AssignmentRow(3, 11), _AssignmentRow(9, 15)])]
    )
    repo = TaxonomyRepo(session=session)

    assignments = await repo.list_final_assignments()

    assert [assignment.model_dump() for assignment in assignments] == [
        {"node_id": 3, "taxonomy_leaf_id": 11},
        {"node_id": 9, "taxonomy_leaf_id": 15},
    ]
