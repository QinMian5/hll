"""
Abstract: Integration tests for ingestion-time hybrid edge initialization
candidate retrieval.
Out of scope: Worker queue execution and HTTP route behavior.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.knowledge_graph.repo import KnowledgeRepo

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


def _embedding(first: float, second: float) -> list[float]:
    return [first, second, *([0.0] * 1534)]


async def _create_node(
    db_session: AsyncSession,
    *,
    title: str,
    content: str = "Existing card content.",
    embedding: list[float] | None = None,
) -> Node:
    node = Node(title=title, content=content, embedding=embedding or _embedding(0.0, 0.0))
    db_session.add(node)
    await db_session.flush()
    return node


async def test_title_mention_candidates_match_complete_title_phrase(
    db_session: AsyncSession,
) -> None:
    phrase_match = await _create_node(
        db_session,
        title="Quantum Mechanics",
        embedding=_embedding(1.0, 0.0),
    )
    await _create_node(
        db_session,
        title="Map",
        embedding=_embedding(1.0, 0.0),
    )
    await _create_node(
        db_session,
        title="Relativity",
        embedding=_embedding(1.0, 0.0),
    )
    repo = KnowledgeRepo(session=db_session)

    candidates = await repo.search_title_mention_candidates(
        content="Quantum Mechanics is referenced directly. Mappings are not the target title.",
        query_embedding=_embedding(1.0, 0.0),
        excluded_node_ids=[],
        limit=5,
    )

    assert [candidate.node_id for candidate in candidates] == [phrase_match.id]


async def test_title_mention_candidates_order_by_similarity_then_node_id(
    db_session: AsyncSession,
) -> None:
    lower_similarity = await _create_node(
        db_session,
        title="Quantum Mechanics",
        embedding=_embedding(0.6, 0.0),
    )
    first_high_similarity = await _create_node(
        db_session,
        title="Special Relativity",
        embedding=_embedding(1.0, 0.0),
    )
    second_high_similarity = await _create_node(
        db_session,
        title="Classical Mechanics",
        embedding=_embedding(1.0, 0.0),
    )
    repo = KnowledgeRepo(session=db_session)

    candidates = await repo.search_title_mention_candidates(
        content=(
            "Quantum Mechanics, Special Relativity, and Classical Mechanics are all referenced."
        ),
        query_embedding=_embedding(1.0, 0.0),
        excluded_node_ids=[],
        limit=3,
    )

    assert [candidate.node_id for candidate in candidates] == [
        first_high_similarity.id,
        second_high_similarity.id,
        lower_similarity.id,
    ]


async def test_semantic_candidates_respect_supplied_candidate_limit(
    db_session: AsyncSession,
) -> None:
    closest = await _create_node(
        db_session,
        title="Closest",
        embedding=_embedding(1.0, 0.0),
    )
    next_closest = await _create_node(
        db_session,
        title="Next Closest",
        embedding=_embedding(0.9, 0.0),
    )
    await _create_node(
        db_session,
        title="Excluded By Limit",
        embedding=_embedding(0.8, 0.0),
    )
    repo = KnowledgeRepo(session=db_session)

    candidates = await repo.search_similarity_candidates(
        query_embedding=_embedding(1.0, 0.0),
        excluded_node_ids=[],
        limit=2,
    )

    assert [candidate.node_id for candidate in candidates] == [closest.id, next_closest.id]
