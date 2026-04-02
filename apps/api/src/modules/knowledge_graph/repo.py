"""
Abstract: Async SQLAlchemy repository primitives for knowledge persistence.
Out of scope: HTTP concerns and cross-module orchestration policy.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.dto import (
    ConnectedTitleCandidate,
    KnowledgeCardMatch,
    SimilarNodeCandidate,
)
from modules.knowledge_graph.model import Adjacency, Edge, Node


def _canonical_edge_pair(node_a_id: int, node_b_id: int) -> tuple[int, int]:
    if node_a_id == node_b_id:
        raise ValueError("Edge endpoints must refer to distinct nodes.")
    if node_a_id < node_b_id:
        return (node_a_id, node_b_id)
    return (node_b_id, node_a_id)


def _distance_to_similarity(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))


class KnowledgeRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def search_top_cards_by_cosine(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]:
        cosine_distance = Node.embedding.cosine_distance(query_embedding)
        statement = (
            select(Node.id, Node.title, Node.content)
            .order_by(cosine_distance.asc(), Node.id.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            KnowledgeCardMatch(node_id=row.id, title=row.title, content=row.content)
            for row in rows
        ]

    async def fetch_connected_title_candidates(
        self,
        *,
        matched_node_ids: Sequence[int],
    ) -> list[ConnectedTitleCandidate]:
        if not matched_node_ids:
            return []

        neighbor_node_id = case(
            (Edge.node_a_id == Adjacency.node_id, Edge.node_b_id),
            else_=Edge.node_a_id,
        ).label("neighbor_node_id")
        statement = (
            select(neighbor_node_id, Node.title)
            .select_from(Adjacency)
            .join(Edge, Edge.id == Adjacency.edge_id)
            .join(Node, Node.id == neighbor_node_id)
            .where(Adjacency.node_id.in_(matched_node_ids))
            .where(neighbor_node_id.not_in(matched_node_ids))
            .order_by(Adjacency.node_id.asc(), neighbor_node_id.asc(), Node.title.asc())
        )
        rows = (await self._session.execute(statement)).all()
        return [
            ConnectedTitleCandidate(node_id=row.neighbor_node_id, title=row.title)
            for row in rows
        ]

    async def create_node(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        node = Node(title=title, content=content, embedding=embedding)
        self._session.add(node)
        await self._session.flush()
        return node.id

    async def search_similarity_candidates(
        self,
        *,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
    ) -> list[SimilarNodeCandidate]:
        cosine_distance = Node.embedding.cosine_distance(query_embedding).label(
            "distance"
        )
        statement = select(Node.id, cosine_distance).order_by(
            cosine_distance.asc(),
            Node.id.asc(),
        )
        if excluded_node_ids:
            statement = statement.where(Node.id.not_in(excluded_node_ids))
        rows = (await self._session.execute(statement)).all()
        return [
            SimilarNodeCandidate(
                node_id=row.id,
                similarity=_distance_to_similarity(float(row.distance)),
            )
            for row in rows
        ]

    async def create_edge_with_adjacency(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> None:
        node_a_id, node_b_id = _canonical_edge_pair(source_node_id, related_node_id)
        edge = Edge(node_a_id=node_a_id, node_b_id=node_b_id, strength=strength)
        self._session.add(edge)
        await self._session.flush()

        self._session.add_all(
            [
                Adjacency(node_id=source_node_id, edge_id=edge.id),
                Adjacency(node_id=related_node_id, edge_id=edge.id),
            ]
        )
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
