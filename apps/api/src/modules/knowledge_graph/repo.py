"""
Abstract: Async SQLAlchemy repository primitives for knowledge persistence.
Out of scope: HTTP concerns and cross-module orchestration policy.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import case, column, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.dto import (
    ConnectedTitleCandidate,
    KnowledgeCardMatch,
    SemanticMapProjectionEdge,
    SemanticMapProjectionNode,
    SimilarNodeCandidate,
    TaxonomyClassificationNodeInput,
)
from modules.knowledge_graph.model import Adjacency, Edge, Node

_NODE_TAXONOMY_ASSIGNMENTS = table(
    "node_taxonomy_assignments",
    column("node_id"),
)


def _canonical_edge_pair(node_a_id: int, node_b_id: int) -> tuple[int, int]:
    if node_a_id == node_b_id:
        raise ValueError("Edge endpoints must refer to distinct nodes.")
    if node_a_id < node_b_id:
        return (node_a_id, node_b_id)
    return (node_b_id, node_a_id)


def _dot_product_to_similarity(dot_product: float) -> float:
    return max(0.0, min(1.0, (dot_product + 1.0) / 2.0))


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
            KnowledgeCardMatch(node_id=row.id, title=row.title, content=row.content) for row in rows
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
            ConnectedTitleCandidate(node_id=row.neighbor_node_id, title=row.title) for row in rows
        ]

    async def fetch_projection_nodes(self) -> list[SemanticMapProjectionNode]:
        rows = (
            await self._session.execute(
                select(Node.id, Node.title, Node.embedding).order_by(Node.id.asc())
            )
        ).all()
        return [
            SemanticMapProjectionNode(
                node_id=row.id,
                title=row.title,
                embedding=row.embedding,
            )
            for row in rows
        ]

    async def fetch_projection_nodes_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[SemanticMapProjectionNode]:
        if not node_ids:
            return []

        rows = (
            await self._session.execute(
                select(Node.id, Node.title, Node.embedding)
                .where(Node.id.in_(node_ids))
                .order_by(Node.id.asc())
            )
        ).all()
        return [
            SemanticMapProjectionNode(
                node_id=row.id,
                title=row.title,
                embedding=row.embedding,
            )
            for row in rows
        ]

    async def fetch_projection_edges_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[SemanticMapProjectionEdge]:
        if not node_ids:
            return []

        rows = (
            await self._session.execute(
                select(Edge.node_a_id, Edge.node_b_id, Edge.strength)
                .where(Edge.node_a_id.in_(node_ids), Edge.node_b_id.in_(node_ids))
                .order_by(Edge.id.asc())
            )
        ).all()
        return [
            SemanticMapProjectionEdge(
                node_a_id=row.node_a_id,
                node_b_id=row.node_b_id,
                strength=row.strength,
            )
            for row in rows
        ]

    async def fetch_unassigned_nodes_for_taxonomy_classification(
        self,
        *,
        limit: int | None,
    ) -> list[TaxonomyClassificationNodeInput]:
        statement = (
            select(Node.id, Node.title, Node.content)
            .outerjoin(
                _NODE_TAXONOMY_ASSIGNMENTS,
                _NODE_TAXONOMY_ASSIGNMENTS.c.node_id == Node.id,
            )
            .where(_NODE_TAXONOMY_ASSIGNMENTS.c.node_id.is_(None))
            .order_by(Node.id.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)

        rows = (await self._session.execute(statement)).all()
        return [
            TaxonomyClassificationNodeInput(
                node_id=row.id,
                title=row.title,
                content=row.content,
            )
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
        neg_inner_product = Node.embedding.max_inner_product(query_embedding).label(
            "neg_inner_product"
        )
        statement = select(Node.id, neg_inner_product).order_by(
            neg_inner_product.asc(),
            Node.id.asc(),
        )
        if excluded_node_ids:
            statement = statement.where(Node.id.not_in(excluded_node_ids))
        rows = (await self._session.execute(statement)).all()
        return [
            SimilarNodeCandidate(
                node_id=row.id,
                # pgvector <#> returns negative inner product for index-friendly ASC order.
                similarity=_dot_product_to_similarity(-float(row.neg_inner_product)),
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
