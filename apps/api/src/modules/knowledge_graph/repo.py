"""
Abstract: Async SQLAlchemy repository primitives for knowledge persistence.
Out of scope: HTTP concerns and cross-module orchestration policy.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import case, column, delete, func, insert, select, table, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.dto import (
    CardProposalRecord,
    CardProposalStatus,
    CardProposalType,
    CardSuggestedEditRecord,
    CardSuggestedEditStatus,
    CardVersionSnapshot,
    ConnectedTitleCandidate,
    KnowledgeCardMatch,
    LexicalSearchCandidate,
    ProjectionCardNode,
    ProjectionCardTitle,
    ProjectionEdge,
    SimilarNodeCandidate,
    TaxonomyClassificationNodeInput,
    VectorSearchCandidate,
)
from modules.knowledge_graph.edge_rebuild import PlannedEdge, RebuildNodeEmbedding
from modules.knowledge_graph.model import (
    Adjacency,
    CardProposal,
    CardVersion,
    Edge,
    Node,
    ProposalApplyAudit,
    WorkspaceRole,
)

_NODE_TAXONOMY_ASSIGNMENTS = table(
    "node_taxonomy_assignments",
    column("node_id"),
)
_EDGE_ID_QUERY_CHUNK_SIZE = 50_000


def _canonical_edge_pair(node_a_id: int, node_b_id: int) -> tuple[int, int]:
    if node_a_id == node_b_id:
        raise ValueError("Edge endpoints must refer to distinct nodes.")
    if node_a_id < node_b_id:
        return (node_a_id, node_b_id)
    return (node_b_id, node_a_id)


def _chunk_unique_ids(values: Sequence[int], *, chunk_size: int) -> Iterator[tuple[int, ...]]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than or equal to 1.")

    seen: set[int] = set()
    chunk: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        chunk.append(value)
        if len(chunk) == chunk_size:
            yield tuple(chunk)
            chunk = []
    if chunk:
        yield tuple(chunk)


def _dot_product_to_similarity(dot_product: float) -> float:
    return max(0.0, min(1.0, (dot_product + 1.0) / 2.0))


def _normalize_search_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _search_tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", _normalize_search_text(value)))


def _title_match_boost(*, title: str, query_text: str) -> tuple[int, int, int]:
    normalized_title = _normalize_search_text(title)
    normalized_query = _normalize_search_text(query_text)
    query_tokens = _search_tokens(query_text)
    title_tokens = set(_search_tokens(title))
    if not normalized_query or not query_tokens:
        return (0, 0, 0)

    exact_title_match = normalized_title == normalized_query
    title_phrase_match = normalized_query in normalized_title
    title_all_tokens_match = all(token in title_tokens for token in query_tokens)
    return (
        int(exact_title_match),
        int(title_phrase_match),
        int(title_all_tokens_match),
    )


def _proposal_record(proposal: CardProposal) -> CardProposalRecord:
    return CardProposalRecord(
        id=proposal.id,
        proposal_type=cast(CardProposalType, proposal.proposal_type),
        reason=proposal.reason,
        status=cast(CardProposalStatus, proposal.status),
        submitted_by_user_id=proposal.submitted_by_user_id,
        reviewed_by_user_id=proposal.reviewed_by_user_id,
        review_note=proposal.review_note,
        payload=proposal.payload,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        reviewed_at=proposal.reviewed_at,
    )


class KnowledgeRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def search_top_cards_by_cosine(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]:
        candidates = await self.search_vector_candidates(
            query_embedding=query_embedding,
            limit=limit,
        )
        return [
            KnowledgeCardMatch(
                node_id=candidate.node_id,
                current_version=candidate.current_version,
                title=candidate.title,
                content=candidate.content,
            )
            for candidate in candidates
        ]

    async def search_vector_candidates(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[VectorSearchCandidate]:
        cosine_distance = Node.embedding.cosine_distance(query_embedding)
        statement = (
            select(Node.id, Node.current_version, Node.title, Node.content)
            .where(Node.lifecycle_state == "active")
            .order_by(cosine_distance.asc(), Node.id.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            VectorSearchCandidate(
                node_id=row.id,
                current_version=row.current_version,
                title=row.title,
                content=row.content,
                vector_rank=index,
            )
            for index, row in enumerate(rows, start=1)
        ]

    async def search_lexical_candidates(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> list[LexicalSearchCandidate]:
        stripped_query = query_text.strip()
        if not stripped_query or limit <= 0:
            return []

        normalized_query = _normalize_search_text(stripped_query)
        lowered_title = func.lower(Node.title)
        ts_query = func.websearch_to_tsquery("english", stripped_query)
        exact_title_match = (lowered_title == normalized_query).label("exact_title_match")
        title_phrase_match = (func.strpos(lowered_title, normalized_query) > 0).label(
            "title_phrase_match"
        )
        title_all_tokens_match = (func.to_tsvector("english", Node.title).op("@@")(ts_query)).label(
            "title_all_tokens_match"
        )
        rank = func.ts_rank_cd(Node.search_vector, ts_query).label("lexical_score")
        statement = (
            select(
                Node.id,
                Node.current_version,
                Node.title,
                Node.content,
                rank,
                exact_title_match,
                title_phrase_match,
                title_all_tokens_match,
            )
            .where(Node.lifecycle_state == "active")
            .where(Node.search_vector.op("@@")(ts_query))
            .order_by(
                exact_title_match.desc(),
                title_phrase_match.desc(),
                title_all_tokens_match.desc(),
                rank.desc(),
                Node.id.asc(),
            )
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            LexicalSearchCandidate(
                node_id=row.id,
                current_version=row.current_version,
                title=row.title,
                content=row.content,
                lexical_rank=index,
                lexical_score=float(row.lexical_score),
                exact_title_match=bool(row.exact_title_match),
                title_phrase_match=bool(row.title_phrase_match),
                title_all_tokens_match=bool(row.title_all_tokens_match),
            )
            for index, row in enumerate(rows, start=1)
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
            .where(Node.lifecycle_state == "active")
            .where(neighbor_node_id.not_in(matched_node_ids))
            .order_by(Adjacency.node_id.asc(), neighbor_node_id.asc(), Node.title.asc())
        )
        rows = (await self._session.execute(statement)).all()
        return [
            ConnectedTitleCandidate(node_id=row.neighbor_node_id, title=row.title) for row in rows
        ]

    async def fetch_projection_cards_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionCardNode]:
        if not node_ids:
            return []

        rows = (
            await self._session.execute(
                select(Node.id, Node.current_version, Node.title, Node.content)
                .where(Node.id.in_(node_ids))
                .where(Node.lifecycle_state == "active")
                .order_by(Node.id.asc())
            )
        ).all()
        return [
            ProjectionCardNode(
                node_id=row.id,
                current_version=row.current_version,
                title=row.title,
                content=row.content,
            )
            for row in rows
        ]

    async def fetch_projection_card_titles_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionCardTitle]:
        if not node_ids:
            return []

        rows = (
            await self._session.execute(
                select(Node.id, Node.title)
                .where(Node.id.in_(node_ids))
                .order_by(Node.id.asc())
                .where(Node.lifecycle_state == "active")
            )
        ).all()
        return [
            ProjectionCardTitle(
                node_id=row.id,
                title=row.title,
            )
            for row in rows
        ]

    async def fetch_projection_edges_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionEdge]:
        if not node_ids:
            return []

        rows = (
            await self._session.execute(
                select(Edge.node_a_id, Edge.node_b_id, Edge.strength)
                .where(Edge.node_a_id.in_(node_ids), Edge.node_b_id.in_(node_ids))
                .order_by(Edge.node_a_id.asc(), Edge.node_b_id.asc())
            )
        ).all()
        return [
            ProjectionEdge(
                node_a_id=row.node_a_id,
                node_b_id=row.node_b_id,
                strength=row.strength,
            )
            for row in rows
        ]

    async def fetch_projection_edges_touching_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionEdge]:
        if not node_ids:
            return []

        rows = (
            await self._session.execute(
                select(Edge.node_a_id, Edge.node_b_id, Edge.strength)
                .distinct()
                .select_from(Adjacency)
                .join(Edge, Edge.id == Adjacency.edge_id)
                .where(Adjacency.node_id.in_(node_ids))
                .order_by(Edge.node_a_id.asc(), Edge.node_b_id.asc())
            )
        ).all()
        return [
            ProjectionEdge(
                node_a_id=row.node_a_id,
                node_b_id=row.node_b_id,
                strength=row.strength,
            )
            for row in rows
        ]

    async def fetch_projection_edges_for_edge_ids(
        self,
        *,
        edge_ids: Sequence[int],
    ) -> list[ProjectionEdge]:
        if not edge_ids:
            return []

        edges: list[ProjectionEdge] = []
        for edge_id_chunk in _chunk_unique_ids(
            edge_ids,
            chunk_size=_EDGE_ID_QUERY_CHUNK_SIZE,
        ):
            rows = (
                await self._session.execute(
                    select(Edge.node_a_id, Edge.node_b_id, Edge.strength)
                    .where(Edge.id.in_(edge_id_chunk))
                    .order_by(Edge.node_a_id.asc(), Edge.node_b_id.asc())
                )
            ).all()
            edges.extend(
                ProjectionEdge(
                    node_a_id=row.node_a_id,
                    node_b_id=row.node_b_id,
                    strength=row.strength,
                )
                for row in rows
            )
        return sorted(edges, key=lambda edge: (edge.node_a_id, edge.node_b_id))

    async def fetch_adjacent_edge_ids_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[int]:
        if not node_ids:
            return []

        rows = (
            await self._session.execute(
                select(Adjacency.edge_id)
                .distinct()
                .where(Adjacency.node_id.in_(node_ids))
                .order_by(Adjacency.edge_id.asc())
            )
        ).all()
        return [row.edge_id for row in rows]

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
            .where(Node.lifecycle_state == "active")
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
        self._session.add(
            CardVersion(
                node_id=node.id,
                version=node.current_version,
                title=title,
                content=content,
            )
        )
        await self._session.flush()
        return node.id

    async def fetch_card_version(
        self,
        *,
        node_id: int,
        version: int,
    ) -> CardVersionSnapshot | None:
        row = (
            await self._session.execute(
                select(
                    CardVersion.node_id,
                    CardVersion.version,
                    CardVersion.title,
                    CardVersion.content,
                )
                .where(CardVersion.node_id == node_id)
                .where(CardVersion.version == version)
                .limit(1)
            )
        ).one_or_none()
        if row is None:
            return None
        return CardVersionSnapshot(
            node_id=row.node_id,
            version=row.version,
            title=row.title,
            content=row.content,
        )

    async def create_card_suggested_edit(
        self,
        *,
        node_id: int,
        base_version: int,
        suggested_title: str,
        suggested_content: str,
        suggested_by_user_id: str,
        reason: str,
    ) -> CardSuggestedEditRecord:
        proposal = CardProposal(
            proposal_type="edit",
            submitted_by_user_id=suggested_by_user_id,
            reason=reason,
            payload={
                "target_node_id": node_id,
                "base_version": base_version,
                "suggested_title": suggested_title,
                "suggested_content": suggested_content,
            },
            status="pending_review",
        )
        self._session.add(proposal)
        await self._session.flush()
        return CardSuggestedEditRecord(
            id=proposal.id,
            node_id=node_id,
            base_version=base_version,
            suggested_title=suggested_title,
            suggested_content=suggested_content,
            suggested_by_user_id=suggested_by_user_id,
            status=cast(CardSuggestedEditStatus, "pending"),
            created_at=proposal.created_at,
        )

    async def create_card_proposal(
        self,
        *,
        proposal_type: str,
        submitted_by_user_id: str,
        reason: str,
        payload: dict[str, object],
    ) -> CardProposalRecord:
        proposal = CardProposal(
            proposal_type=proposal_type,
            submitted_by_user_id=submitted_by_user_id,
            reason=reason,
            payload=payload,
            status="pending_review",
        )
        self._session.add(proposal)
        await self._session.flush()
        return _proposal_record(proposal)

    async def fetch_card_proposal(self, *, proposal_id: int) -> CardProposalRecord | None:
        proposal = await self._session.scalar(
            select(CardProposal).where(CardProposal.id == proposal_id).limit(1)
        )
        if proposal is None:
            return None
        return _proposal_record(proposal)

    async def list_card_proposals_for_user(self, *, user_id: str) -> list[CardProposalRecord]:
        proposals = (
            await self._session.scalars(
                select(CardProposal)
                .where(CardProposal.submitted_by_user_id == user_id)
                .order_by(CardProposal.created_at.desc(), CardProposal.id.desc())
            )
        ).all()
        return [_proposal_record(proposal) for proposal in proposals]

    async def list_pending_card_proposals(self) -> list[CardProposalRecord]:
        proposals = (
            await self._session.scalars(
                select(CardProposal)
                .where(CardProposal.status == "pending_review")
                .order_by(CardProposal.created_at.asc(), CardProposal.id.asc())
            )
        ).all()
        return [_proposal_record(proposal) for proposal in proposals]

    async def has_active_workspace_review_role(self, *, user_id: str) -> bool:
        role = await self._session.scalar(
            select(WorkspaceRole.id)
            .where(WorkspaceRole.user_id == user_id)
            .where(WorkspaceRole.role.in_(("reviewer", "admin")))
            .where(WorkspaceRole.revoked_at.is_(None))
            .limit(1)
        )
        return role is not None

    async def create_next_card_version(
        self,
        *,
        node_id: int,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        node = await self._session.scalar(
            select(Node).where(Node.id == node_id).where(Node.lifecycle_state == "active").limit(1)
        )
        if node is None:
            raise ValueError("Target node does not exist.")

        next_version = node.current_version + 1
        node.title = title
        node.content = content
        node.embedding = embedding
        node.current_version = next_version
        self._session.add(
            CardVersion(
                node_id=node.id,
                version=next_version,
                title=title,
                content=content,
            )
        )
        await self._session.flush()
        return next_version

    async def archive_node(self, *, node_id: int) -> None:
        await self._session.execute(
            update(Node)
            .where(Node.id == node_id)
            .where(Node.lifecycle_state == "active")
            .values(lifecycle_state="archived")
        )
        await self._session.flush()

    async def mark_card_proposal_accepted(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
        affected_node_ids: list[int],
        created_versions: list[dict[str, int]],
        archive_outcome: dict[str, object] | None,
    ) -> CardProposalRecord:
        proposal = await self._transition_card_proposal(
            proposal_id=proposal_id,
            status="accepted_applied",
            reviewer_user_id=reviewer_user_id,
            review_note=review_note,
        )
        return _proposal_record(proposal)

    async def mark_card_proposal_rejected(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
    ) -> CardProposalRecord:
        proposal = await self._transition_card_proposal(
            proposal_id=proposal_id,
            status="rejected",
            reviewer_user_id=reviewer_user_id,
            review_note=review_note,
        )
        return _proposal_record(proposal)

    async def mark_card_proposal_withdrawn(
        self,
        *,
        proposal_id: int,
    ) -> CardProposalRecord:
        proposal = await self._transition_card_proposal(
            proposal_id=proposal_id,
            status="withdrawn",
            reviewer_user_id=None,
            review_note=None,
        )
        return _proposal_record(proposal)

    async def _transition_card_proposal(
        self,
        *,
        proposal_id: int,
        status: str,
        reviewer_user_id: str | None,
        review_note: str | None,
    ) -> CardProposal:
        proposal = await self._session.scalar(
            select(CardProposal).where(CardProposal.id == proposal_id).limit(1)
        )
        if proposal is None:
            raise ValueError("Proposal does not exist.")
        now = datetime.now(UTC)
        proposal.status = status
        proposal.reviewed_by_user_id = reviewer_user_id
        proposal.review_note = review_note
        proposal.reviewed_at = now
        await self._session.flush()
        return proposal

    async def create_proposal_apply_audit(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        proposal_type: str,
        affected_node_ids: list[int],
        created_versions: list[dict[str, int]],
        archive_outcome: dict[str, object] | None,
        review_note: str | None,
    ) -> None:
        self._session.add(
            ProposalApplyAudit(
                proposal_id=proposal_id,
                reviewer_user_id=reviewer_user_id,
                proposal_type=proposal_type,
                affected_node_ids=affected_node_ids,
                created_versions=created_versions,
                archive_outcome=archive_outcome,
                review_note=review_note,
            )
        )
        await self._session.flush()

    async def fetch_node_ids_in_rebuild_order(self) -> list[int]:
        rows = (await self._session.execute(select(Node.id).order_by(Node.id.asc()))).all()
        return [row.id for row in rows]

    async def fetch_rebuild_nodes_with_embeddings(self) -> list[RebuildNodeEmbedding]:
        nodes = await self._session.scalars(select(Node).order_by(Node.id.asc()))
        return [
            RebuildNodeEmbedding(node_id=node.id, embedding=node.embedding) for node in nodes.all()
        ]

    async def search_similarity_candidates(
        self,
        *,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
        limit: int,
    ) -> list[SimilarNodeCandidate]:
        if limit <= 0:
            return []

        neg_inner_product = Node.embedding.max_inner_product(query_embedding).label(
            "neg_inner_product"
        )
        statement = (
            select(Node.id, neg_inner_product)
            .order_by(
                neg_inner_product.asc(),
                Node.id.asc(),
            )
            .limit(limit)
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

    async def search_title_mention_candidates(
        self,
        *,
        content: str,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
        limit: int,
    ) -> list[SimilarNodeCandidate]:
        if limit <= 0:
            return []

        neg_inner_product = Node.embedding.max_inner_product(query_embedding).label(
            "neg_inner_product"
        )
        content_vector = func.to_tsvector("simple", content)
        title_phrase_query = func.phraseto_tsquery("simple", Node.title)
        statement = (
            select(Node.id, neg_inner_product)
            .where(content_vector.op("@@")(title_phrase_query))
            .order_by(
                neg_inner_product.asc(),
                Node.id.asc(),
            )
            .limit(limit)
        )
        if excluded_node_ids:
            statement = statement.where(Node.id.not_in(excluded_node_ids))
        rows = (await self._session.execute(statement)).all()
        return [
            SimilarNodeCandidate(
                node_id=row.id,
                similarity=_dot_product_to_similarity(-float(row.neg_inner_product)),
            )
            for row in rows
        ]

    async def search_historical_similarity_candidates(
        self,
        *,
        source_node_id: int,
    ) -> list[SimilarNodeCandidate]:
        source_node = await self._session.scalar(
            select(Node).where(Node.id == source_node_id).limit(1)
        )
        if source_node is None:
            return []

        neg_inner_product = Node.embedding.max_inner_product(source_node.embedding).label(
            "neg_inner_product"
        )
        statement = (
            select(Node.id, neg_inner_product)
            .where(Node.id < source_node_id)
            .order_by(
                neg_inner_product.asc(),
                Node.id.asc(),
            )
        )
        rows = (await self._session.execute(statement)).all()
        return [
            SimilarNodeCandidate(
                node_id=row.id,
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
    ) -> int:
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
        return edge.id

    async def clear_edges_with_adjacency(self) -> None:
        await self._session.execute(delete(Adjacency))
        await self._session.execute(delete(Edge))
        await self._session.flush()

    async def replace_edges_with_adjacency(
        self,
        *,
        planned_edges: Sequence[PlannedEdge],
    ) -> int:
        await self.clear_edges_with_adjacency()
        if not planned_edges:
            return 0

        edge_rows = [
            {
                "node_a_id": edge.related_node_id,
                "node_b_id": edge.source_node_id,
                "strength": edge.strength,
            }
            for edge in planned_edges
        ]
        edge_result = await self._session.execute(
            insert(Edge).returning(Edge.id, Edge.node_a_id, Edge.node_b_id),
            edge_rows,
        )
        inserted_edges = edge_result.all()
        adjacency_rows = [
            {"node_id": node_id, "edge_id": edge.id}
            for edge in inserted_edges
            for node_id in (edge.node_a_id, edge.node_b_id)
        ]
        await self._session.execute(insert(Adjacency), adjacency_rows)
        await self._session.flush()
        return len(inserted_edges)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
