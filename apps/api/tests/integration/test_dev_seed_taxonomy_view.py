"""
Abstract: Integration tests for the development taxonomy-view placeholder seed.
Out of scope: CLI parsing and browser-side visualization behavior.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from entrypoints.ops.dev_seed_taxonomy_view import seed_dev_taxonomy_view
from modules.knowledge_graph.model import Adjacency, Edge, Node
from modules.taxonomy.model import (
    NodeTaxonomyAssignment,
    TaxonomyNode,
    TaxonomyScopeProjectionEdge,
)

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


async def test_seed_dev_taxonomy_view_writes_placeholder_graph(
    db_session: AsyncSession,
) -> None:
    first_result = await seed_dev_taxonomy_view(session=db_session, reset=True)
    second_result = await seed_dev_taxonomy_view(session=db_session, reset=True)

    taxonomy_names = (
        await db_session.scalars(select(TaxonomyNode.name).order_by(TaxonomyNode.name.asc()))
    ).all()
    card_titles = (await db_session.scalars(select(Node.title).order_by(Node.title.asc()))).all()
    edge_count = await db_session.scalar(select(func.count()).select_from(Edge))
    adjacency_count = await db_session.scalar(select(func.count()).select_from(Adjacency))
    assignment_count = await db_session.scalar(
        select(func.count()).select_from(NodeTaxonomyAssignment)
    )
    projection_count = await db_session.scalar(
        select(func.count()).select_from(TaxonomyScopeProjectionEdge)
    )

    assert first_result.taxonomy_node_count == 7
    assert first_result.card_count == 8
    assert first_result.edge_count == 9
    assert second_result.taxonomy_node_count == 7
    assert second_result.card_count == 8
    assert second_result.edge_count == 9
    assert taxonomy_names == [
        "Branch1",
        "Branch2",
        "Leaf1",
        "Leaf2",
        "Leaf3",
        "Leaf4",
        "Root",
    ]
    assert card_titles == [
        "Card1",
        "Card2",
        "Card3",
        "Card4",
        "Card5",
        "Card6",
        "Card7",
        "Card8",
    ]
    assert edge_count == 9
    assert adjacency_count == 18
    assert assignment_count == 8
    assert projection_count is not None
    assert projection_count >= 9
