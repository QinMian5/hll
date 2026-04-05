"""
Abstract: Integration tests for the taxonomy leaf-only assignment trigger.
Out of scope: Import bootstrap behavior and taxonomy HTTP transport contracts.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode


async def _create_knowledge_node(db_session: AsyncSession) -> Node:
    node = Node(
        title="Card title",
        content="Card content",
        embedding=[0.1] * 1536,
    )
    db_session.add(node)
    await db_session.flush()
    return node


async def _create_taxonomy_node(
    db_session: AsyncSession,
    *,
    name: str,
    depth: int,
    is_leaf: bool,
    parent_id: int | None = None,
) -> TaxonomyNode:
    taxonomy_node = TaxonomyNode(
        parent_id=parent_id,
        name=name,
        depth=depth,
        is_leaf=is_leaf,
    )
    db_session.add(taxonomy_node)
    await db_session.flush()
    return taxonomy_node


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_assignment_to_non_leaf_taxonomy_node_is_rejected(
    db_session: AsyncSession,
) -> None:
    knowledge_node = await _create_knowledge_node(db_session)
    parent = await _create_taxonomy_node(
        db_session,
        name="Science",
        depth=0,
        is_leaf=False,
    )

    db_session.add(
        NodeTaxonomyAssignment(
            node_id=knowledge_node.id,
            taxonomy_node_id=parent.id,
            assigned_at=datetime.now(UTC),
        )
    )

    with pytest.raises(DBAPIError):
        await db_session.flush()


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_assignment_to_leaf_taxonomy_node_is_accepted(
    db_session: AsyncSession,
) -> None:
    knowledge_node = await _create_knowledge_node(db_session)
    parent = await _create_taxonomy_node(
        db_session,
        name="Science",
        depth=0,
        is_leaf=False,
    )
    leaf = await _create_taxonomy_node(
        db_session,
        name="Mathematics",
        depth=1,
        is_leaf=True,
        parent_id=parent.id,
    )

    assignment = NodeTaxonomyAssignment(
        node_id=knowledge_node.id,
        taxonomy_node_id=leaf.id,
        assigned_at=datetime.now(UTC),
    )
    db_session.add(assignment)
    await db_session.flush()

    assert assignment.id is not None
