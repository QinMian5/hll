"""
Abstract: Integration tests for historical card assignment backfill into Root.
Out of scope: Operator CLI parsing and live production execution.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.root_assignment_backfill import (
    TaxonomyRootAssignmentBackfillService,
)

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


async def _create_node(db_session: AsyncSession, *, title: str) -> Node:
    node = Node(title=title, content=f"{title} content.", embedding=[0.1] * 1536)
    db_session.add(node)
    await db_session.flush()
    return node


async def test_backfill_assigns_only_historical_cards_without_current_assignment(
    db_session: AsyncSession,
) -> None:
    assigned_node = await _create_node(db_session, title="Assigned")
    missing_node = await _create_node(db_session, title="Missing")
    existing_root = TaxonomyNode(parent_id=None, name="Root", route_slug="root", depth=0)
    db_session.add(existing_root)
    await db_session.flush()
    science = TaxonomyNode(
        parent_id=existing_root.id,
        name="Science",
        route_slug="science",
        depth=1,
    )
    db_session.add(science)
    await db_session.flush()
    db_session.add(
        NodeTaxonomyAssignment(
            node_id=assigned_node.id,
            taxonomy_node_id=science.id,
        )
    )
    await db_session.commit()

    service = TaxonomyRootAssignmentBackfillService(repo=TaxonomyRepo(session=db_session))

    result = await service.run(apply=True)
    assigned_assignment = await db_session.scalar(
        select(NodeTaxonomyAssignment).where(NodeTaxonomyAssignment.node_id == assigned_node.id)
    )
    missing_assignment = await db_session.scalar(
        select(NodeTaxonomyAssignment).where(NodeTaxonomyAssignment.node_id == missing_node.id)
    )

    assert result.root_id == existing_root.id
    assert result.total_cards == 2
    assert result.assigned_before == 1
    assert result.missing_before == 1
    assert result.inserted_assignments == 1
    assert result.missing_after == 0
    assert assigned_assignment is not None
    assert assigned_assignment.taxonomy_node_id == science.id
    assert missing_assignment is not None
    assert missing_assignment.taxonomy_node_id == existing_root.id


async def test_backfill_apply_is_idempotent_after_first_run(db_session: AsyncSession) -> None:
    await _create_node(db_session, title="Only Card")
    await db_session.commit()
    service = TaxonomyRootAssignmentBackfillService(repo=TaxonomyRepo(session=db_session))

    first_result = await service.run(apply=True)
    second_result = await service.run(apply=True)
    assignment_count = await db_session.scalar(
        select(func.count()).select_from(NodeTaxonomyAssignment)
    )

    assert first_result.inserted_assignments == 1
    assert first_result.missing_after == 0
    assert second_result.inserted_assignments == 0
    assert second_result.missing_before == 0
    assert assignment_count == 1
