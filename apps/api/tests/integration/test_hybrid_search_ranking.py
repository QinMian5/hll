"""
Abstract: PostgreSQL-backed acceptance tests for hybrid card search ranking.
Out of scope: HTTP response shaping and embedding-provider integration.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.knowledge_graph.repo import KnowledgeRepo
from modules.knowledge_graph.service import KnowledgeGraphService

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


def _embedding(first: float, second: float) -> list[float]:
    return [first, second, *([0.0] * 1534)]


async def _create_node(
    db_session: AsyncSession,
    *,
    title: str,
    content: str,
    embedding: list[float],
) -> Node:
    node = Node(title=title, content=content, embedding=embedding)
    db_session.add(node)
    await db_session.flush()
    return node


def _service(db_session: AsyncSession) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        repo=KnowledgeRepo(session=db_session),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )


async def test_hybrid_search_exact_title_ranks_ahead_of_content_only_match(
    db_session: AsyncSession,
) -> None:
    exact_title = await _create_node(
        db_session,
        title="Quantum Mechanics",
        content="A concise title match.",
        embedding=_embedding(0.1, 0.9),
    )
    content_only = await _create_node(
        db_session,
        title="Physics Notes",
        content="Quantum mechanics appears in content only.",
        embedding=_embedding(0.9, 0.1),
    )

    matches = await _service(db_session).search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=_embedding(1.0, 0.0),
        limit=2,
    )

    assert [match.node_id for match in matches] == [exact_title.id, content_only.id]


async def test_hybrid_search_title_tokens_rank_ahead_of_content_only_match(
    db_session: AsyncSession,
) -> None:
    token_title = await _create_node(
        db_session,
        title="Mechanics and Quantum Notes",
        content="Title contains both query tokens.",
        embedding=_embedding(0.1, 0.9),
    )
    content_only = await _create_node(
        db_session,
        title="Science Notes",
        content="Quantum mechanics appears in content only.",
        embedding=_embedding(0.9, 0.1),
    )

    matches = await _service(db_session).search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=_embedding(1.0, 0.0),
        limit=2,
    )

    assert [match.node_id for match in matches] == [token_title.id, content_only.id]


async def test_hybrid_search_keeps_vector_only_candidate_when_lexical_has_no_match(
    db_session: AsyncSession,
) -> None:
    semantic_match = await _create_node(
        db_session,
        title="Semantic Recall",
        content="The text intentionally avoids the query term.",
        embedding=_embedding(1.0, 0.0),
    )

    matches = await _service(db_session).search_searchable_cards(
        query_text="nonexistentlexicalterm",
        query_embedding=_embedding(1.0, 0.0),
        limit=1,
    )

    assert [match.node_id for match in matches] == [semantic_match.id]
