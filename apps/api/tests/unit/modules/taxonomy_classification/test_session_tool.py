"""
Abstract: Unit tests for taxonomy-classification session tool contracts.
Out of scope: Cursor subprocess execution and database trigger integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord
from modules.taxonomy.errors import TaxonomyAssignmentAlreadyExistsError
from modules.taxonomy_classification.session_tool import TaxonomyClassificationSessionTool


def _build_assignment(*, node_id: int, leaf_id: int) -> TaxonomyAssignmentRecord:
    return TaxonomyAssignmentRecord(
        id=99,
        node_id=node_id,
        taxonomy_node=TaxonomyNodeRecord(
            id=leaf_id,
            parent_id=1,
            name="Algebra",
            depth=2,
            is_leaf=True,
        ),
        assigned_at=datetime(2026, 4, 6, 10, 0, tzinfo=UTC),
    )


@dataclass(slots=True)
class _StubTaxonomyPort:
    stored_assignment: TaxonomyAssignmentRecord | None = None

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]:
        assert parent_id == 1
        return [
            TaxonomyNodeRecord(id=11, parent_id=1, name="Chemistry", depth=1, is_leaf=True),
            TaxonomyNodeRecord(id=12, parent_id=1, name="Physics", depth=1, is_leaf=True),
        ]

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        assert node_id == 10
        return self.stored_assignment

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord:
        assert node_id == 10
        assert taxonomy_node_id in (7, 8)
        if self.stored_assignment is not None:
            raise TaxonomyAssignmentAlreadyExistsError("node already has final taxonomy assignment")
        self.stored_assignment = _build_assignment(node_id=node_id, leaf_id=taxonomy_node_id)
        return self.stored_assignment


@pytest.mark.anyio
async def test_list_children_returns_name_sorted_children() -> None:
    tool = TaxonomyClassificationSessionTool(taxonomy_port=_StubTaxonomyPort())

    payload = await tool.list_children(parent_id=1)

    assert [item.name for item in payload.children] == ["Chemistry", "Physics"]


@pytest.mark.anyio
async def test_assign_leaf_returns_assigned_on_first_write() -> None:
    tool = TaxonomyClassificationSessionTool(taxonomy_port=_StubTaxonomyPort())

    payload = await tool.assign_leaf(node_id=10, leaf_id=7)

    assert payload.result == "assigned"
    assert payload.assignment.taxonomy_node.id == 7


@pytest.mark.anyio
async def test_assign_leaf_returns_already_assigned_without_overwrite() -> None:
    existing = _build_assignment(node_id=10, leaf_id=7)
    tool = TaxonomyClassificationSessionTool(
        taxonomy_port=_StubTaxonomyPort(stored_assignment=existing)
    )

    payload = await tool.assign_leaf(node_id=10, leaf_id=8)

    assert payload.result == "already_assigned"
    assert payload.assignment.taxonomy_node.id == 7
