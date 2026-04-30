"""
Abstract: Unit tests for taxonomy repository boundary behavior.
Out of scope: Database I/O, trigger enforcement, and service orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.taxonomy import repo as taxonomy_repo_module
from modules.taxonomy.model import (
    NodeTaxonomyAssignment,
    TaxonomyNode,
)
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
    executed_statements: list[object] = field(default_factory=list)
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
        self.executed_statements.append(statement)
        if self.execute_results:
            return self.execute_results.pop(0)
        return _StubExecuteResult()

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed = True


def _repo_with_stub(session: _StubSession) -> TaxonomyRepo:
    return TaxonomyRepo(session=cast(AsyncSession, session))


@pytest.mark.anyio
async def test_create_taxonomy_node_persists_canonical_route_slug() -> None:
    session = _StubSession()
    repo = _repo_with_stub(session)

    await repo.create_taxonomy_node(
        parent_id=1,
        name="Science (General)",
        depth=2,
        is_leaf=False,
    )

    created_node = session.added[0]
    assert isinstance(created_node, TaxonomyNode)
    assert created_node.route_slug == "science-general"
    assert session.flushed is True


@pytest.mark.anyio
async def test_list_tree_nodes_returns_record_models() -> None:
    session = _StubSession(
        scalars_results=[
            _StubScalarResult(
                [
                    TaxonomyNode(
                        id=1,
                        parent_id=None,
                        name="Science",
                        route_slug="science",
                        depth=0,
                        is_leaf=False,
                    ),
                    TaxonomyNode(
                        id=2,
                        parent_id=1,
                        name="Physics",
                        route_slug="physics",
                        depth=1,
                        is_leaf=True,
                    ),
                ]
            )
        ]
    )
    repo = _repo_with_stub(session)

    records = await repo.list_tree_nodes()

    assert [record.model_dump() for record in records] == [
        {
            "id": 1,
            "parent_id": None,
            "name": "Science",
            "route_slug": "science",
            "depth": 0,
            "is_leaf": False,
        },
        {
            "id": 2,
            "parent_id": 1,
            "name": "Physics",
            "route_slug": "physics",
            "depth": 1,
            "is_leaf": True,
        },
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
                        route_slug="algebra",
                        depth=2,
                        is_leaf=True,
                    ),
                )
            )
        ]
    )
    repo = _repo_with_stub(session)

    assignment = await repo.get_assignment_for_node(node_id=12)

    assert assignment is not None
    assert assignment.node_id == 12
    assert assignment.taxonomy_node.name == "Algebra"
    assert assignment.assigned_at == assigned_at


@pytest.mark.anyio
async def test_set_current_assignment_moves_existing_assignment() -> None:
    existing_assignment = NodeTaxonomyAssignment(
        id=7,
        node_id=99,
        taxonomy_node_id=3,
        assigned_at=datetime(2026, 4, 5, 1, 0, tzinfo=UTC),
    )
    session = _StubSession(
        scalar_results=[existing_assignment],
        execute_results=[
            _StubExecuteResult(
                (
                    existing_assignment,
                    TaxonomyNode(
                        id=8,
                        parent_id=3,
                        name="Unclassified",
                        route_slug="unclassified",
                        depth=2,
                        is_leaf=True,
                    ),
                )
            )
        ],
    )
    repo = _repo_with_stub(session)

    assignment = await repo.set_current_assignment(
        node_id=99,
        taxonomy_node_id=8,
    )

    assert existing_assignment.taxonomy_node_id == 8
    assert assignment.taxonomy_node.id == 8
    assert session.flushed is True


@pytest.mark.anyio
async def test_set_current_assignment_creates_when_assignment_missing() -> None:
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
                        route_slug="general",
                        depth=2,
                        is_leaf=True,
                    ),
                )
            )
        ],
    )
    repo = _repo_with_stub(session)

    assignment = await repo.set_current_assignment(
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
    repo = _repo_with_stub(session)

    assignments = await repo.list_final_assignments()

    assert [assignment.model_dump() for assignment in assignments] == [
        {"node_id": 3, "taxonomy_leaf_id": 11},
        {"node_id": 9, "taxonomy_leaf_id": 15},
    ]


@pytest.mark.anyio
async def test_list_leaf_assignment_counts_returns_grouped_leaf_counts() -> None:
    class _AssignmentCountRow:
        def __init__(self, taxonomy_leaf_id: int, card_count: int) -> None:
            self.taxonomy_leaf_id = taxonomy_leaf_id
            self.card_count = card_count

    session = _StubSession(
        execute_results=[
            _StubExecuteResult(
                rows=[
                    _AssignmentCountRow(11, 3),
                    _AssignmentCountRow(15, 8),
                ]
            )
        ]
    )
    repo = _repo_with_stub(session)

    counts = await repo.list_leaf_assignment_counts()

    assert [count.model_dump() for count in counts] == [
        {"taxonomy_leaf_id": 11, "card_count": 3},
        {"taxonomy_leaf_id": 15, "card_count": 8},
    ]


@pytest.mark.anyio
async def test_list_assigned_node_ids_for_leaf_returns_sorted_node_ids_for_one_leaf() -> None:
    class _LeafNodeRow:
        def __init__(self, node_id: int) -> None:
            self.node_id = node_id

    session = _StubSession(
        execute_results=[
            _StubExecuteResult(rows=[_LeafNodeRow(19), _LeafNodeRow(41), _LeafNodeRow(88)])
        ]
    )
    repo = _repo_with_stub(session)

    node_ids = await repo.list_assigned_node_ids_for_leaf(leaf_id=44)

    assert node_ids == [19, 41, 88]


@pytest.mark.anyio
async def test_list_projected_edge_ids_for_leaf_returns_sorted_edge_ids() -> None:
    class _EdgeRow:
        def __init__(self, edge_id: int) -> None:
            self.edge_id = edge_id

    session = _StubSession(
        execute_results=[
            _StubExecuteResult(rows=[_EdgeRow(7), _EdgeRow(18), _EdgeRow(42)]),
        ]
    )
    repo = _repo_with_stub(session)

    edge_ids = await repo.list_projected_edge_ids_for_leaf(leaf_id=44)

    assert edge_ids == [7, 18, 42]


@pytest.mark.anyio
async def test_add_projected_edge_ids_for_leaf_creates_projection_rows() -> None:
    session = _StubSession()
    repo = _repo_with_stub(session)

    await repo.add_projected_edge_ids_for_leaf(leaf_id=44, edge_ids=[7, 18])

    assert session.flushed is True
    assert session.executed_statements


@pytest.mark.anyio
async def test_add_projected_edge_ids_for_leaf_chunks_projection_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        taxonomy_repo_module,
        "TAXONOMY_PROJECTION_EDGE_INSERT_BATCH_SIZE",
        2,
        raising=False,
    )
    session = _StubSession()
    repo = _repo_with_stub(session)

    await repo.add_projected_edge_ids_for_leaf(leaf_id=44, edge_ids=[18, 7, 18, 42, 99, 100])

    assert session.flushed is True
    assert len(session.executed_statements) == 3


@pytest.mark.anyio
async def test_list_leaf_ids_for_node_ids_returns_mapping_for_assigned_nodes() -> None:
    class _LeafRow:
        def __init__(self, node_id: int, taxonomy_node_id: int) -> None:
            self.node_id = node_id
            self.taxonomy_node_id = taxonomy_node_id

    session = _StubSession(
        execute_results=[
            _StubExecuteResult(rows=[_LeafRow(11, 2), _LeafRow(77, 9)]),
        ]
    )
    repo = _repo_with_stub(session)

    mapping = await repo.list_leaf_ids_for_node_ids(node_ids=[77, 11, 999])

    assert mapping == {11: 2, 77: 9}
