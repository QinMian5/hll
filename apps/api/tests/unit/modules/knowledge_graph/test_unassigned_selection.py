"""
Abstract: Unit tests for unassigned-node selection used by taxonomy classification orchestration.
Out of scope: SQL execution against a real database and Cursor session orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.knowledge_graph.repo import KnowledgeRepo


class _StubExecuteResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return list(self._rows)


@dataclass(slots=True)
class _StubSession:
    execute_results: list[_StubExecuteResult] = field(default_factory=list)

    async def execute(self, statement: object) -> _StubExecuteResult:
        assert statement is not None
        return self.execute_results.pop(0)


@pytest.mark.anyio
async def test_fetch_unassigned_nodes_for_taxonomy_classification_with_limit() -> None:
    class _Row:
        def __init__(self, node_id: int, title: str, content: str) -> None:
            self.id = node_id
            self.title = title
            self.content = content

    repo = KnowledgeRepo(
        session=_StubSession(
            execute_results=[
                _StubExecuteResult(
                    rows=[
                        _Row(1, "Card 1", "Content 1"),
                        _Row(2, "Card 2", "Content 2"),
                    ]
                )
            ]
        )
    )

    records = await repo.fetch_unassigned_nodes_for_taxonomy_classification(limit=2)

    assert [record.model_dump() for record in records] == [
        {"node_id": 1, "title": "Card 1", "content": "Content 1"},
        {"node_id": 2, "title": "Card 2", "content": "Content 2"},
    ]


@pytest.mark.anyio
async def test_fetch_unassigned_nodes_for_taxonomy_classification_without_limit() -> None:
    class _Row:
        def __init__(self, node_id: int, title: str, content: str) -> None:
            self.id = node_id
            self.title = title
            self.content = content

    repo = KnowledgeRepo(
        session=_StubSession(
            execute_results=[
                _StubExecuteResult(
                    rows=[
                        _Row(3, "Card 3", "Content 3"),
                        _Row(4, "Card 4", "Content 4"),
                        _Row(5, "Card 5", "Content 5"),
                    ]
                )
            ]
        )
    )

    records = await repo.fetch_unassigned_nodes_for_taxonomy_classification(limit=None)

    assert [record.node_id for record in records] == [3, 4, 5]
