"""
Abstract: Async SQLAlchemy repository primitives for taxonomy bootstrap, tree reads,
and final assignments.
Out of scope: YAML parsing and HTTP transport wiring.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord
from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode


def _taxonomy_node_record_from_model(node: TaxonomyNode) -> TaxonomyNodeRecord:
    return TaxonomyNodeRecord(
        id=node.id,
        parent_id=node.parent_id,
        name=node.name,
        depth=node.depth,
        is_leaf=node.is_leaf,
    )


def _assignment_record_from_row(
    assignment: NodeTaxonomyAssignment,
    taxonomy_node: TaxonomyNode,
) -> TaxonomyAssignmentRecord:
    return TaxonomyAssignmentRecord(
        id=assignment.id,
        node_id=assignment.node_id,
        taxonomy_node=_taxonomy_node_record_from_model(taxonomy_node),
        assigned_at=assignment.assigned_at,
    )


class TaxonomyRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def has_any_taxonomy_nodes(self) -> bool:
        result = await self._session.execute(select(TaxonomyNode.id).limit(1))
        return result.scalar_one_or_none() is not None

    async def create_taxonomy_node(
        self,
        *,
        parent_id: int | None,
        name: str,
        depth: int,
        is_leaf: bool,
    ) -> int:
        taxonomy_node = TaxonomyNode(
            parent_id=parent_id,
            name=name,
            depth=depth,
            is_leaf=is_leaf,
        )
        self._session.add(taxonomy_node)
        await self._session.flush()
        return taxonomy_node.id

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        result = await self._session.scalars(
            select(TaxonomyNode).order_by(
                TaxonomyNode.depth.asc(),
                TaxonomyNode.parent_id.asc().nullsfirst(),
                TaxonomyNode.name.asc(),
                TaxonomyNode.id.asc(),
            )
        )
        return [_taxonomy_node_record_from_model(node) for node in result.all()]

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]:
        statement = select(TaxonomyNode)
        if parent_id is None:
            statement = statement.where(TaxonomyNode.parent_id.is_(None))
        else:
            statement = statement.where(TaxonomyNode.parent_id == parent_id)

        result = await self._session.scalars(
            statement.order_by(TaxonomyNode.name.asc(), TaxonomyNode.id.asc())
        )
        return [_taxonomy_node_record_from_model(node) for node in result.all()]

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        result = await self._session.execute(
            select(NodeTaxonomyAssignment, TaxonomyNode)
            .join(TaxonomyNode, TaxonomyNode.id == NodeTaxonomyAssignment.taxonomy_node_id)
            .where(NodeTaxonomyAssignment.node_id == node_id)
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return None

        assignment, taxonomy_node = row
        return _assignment_record_from_row(assignment, taxonomy_node)

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
        assigned_at: datetime,
    ) -> TaxonomyAssignmentRecord:
        assignment = await self._session.scalar(
            select(NodeTaxonomyAssignment).where(NodeTaxonomyAssignment.node_id == node_id).limit(1)
        )
        if assignment is None:
            assignment = NodeTaxonomyAssignment(
                node_id=node_id,
                taxonomy_node_id=taxonomy_node_id,
                assigned_at=assigned_at,
            )
            self._session.add(assignment)
        else:
            assignment.taxonomy_node_id = taxonomy_node_id
            assignment.assigned_at = assigned_at

        await self._session.flush()
        stored_assignment = await self.get_assignment_for_node(node_id=node_id)
        if stored_assignment is None:
            raise RuntimeError("Final taxonomy assignment was not readable after persistence.")
        return stored_assignment

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
