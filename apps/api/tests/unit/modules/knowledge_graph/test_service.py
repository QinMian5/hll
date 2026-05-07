"""
Abstract: Unit tests for knowledge-graph service orchestration and response-shaping
rules.
Out of scope: SQL statement correctness and FastAPI route wiring.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

import pytest

from modules.knowledge_graph.dto import (
    CardProposalRecord,
    CardProposalType,
    CardSuggestedEditRecord,
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
from modules.knowledge_graph.service import (
    CardProposalPermissionError,
    CardProposalValidationError,
    CardSuggestedEditNoChangeError,
    CardVersionNotFoundError,
    KnowledgeGraphRepoProtocol,
    KnowledgeGraphService,
)
from modules.taxonomy.dto import TaxonomyScopeIdentity


@dataclass(slots=True)
class _StubRepo:
    created_nodes: list[tuple[str, str, list[float]]] | None = None
    created_edges: list[tuple[int, int, float]] | None = None
    card_versions_by_key: dict[tuple[int, int], CardVersionSnapshot] | None = None
    created_suggested_edits: list[tuple[int, int, str, str, str, str]] | None = None
    vector_candidates: list[VectorSearchCandidate] | None = None
    lexical_candidates: list[LexicalSearchCandidate] | None = None
    title_mention_candidates: list[SimilarNodeCandidate] | None = None
    semantic_candidates: list[SimilarNodeCandidate] | None = None
    vector_candidate_limits: list[int] = field(default_factory=list)
    lexical_candidate_limits: list[int] = field(default_factory=list)
    title_mention_limits: list[int] = field(default_factory=list)
    semantic_candidate_limits: list[int] = field(default_factory=list)
    semantic_excluded_node_ids: list[list[int]] = field(default_factory=list)
    next_edge_id: int = 500
    next_suggested_edit_id: int = 700
    committed: bool = False
    rolled_back: bool = False
    fail_on_edge_for_node_id: int | None = None

    async def search_top_cards_by_cosine(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]:
        assert query_embedding
        assert limit == 5
        return [
            KnowledgeCardMatch(node_id=1, current_version=1, title="Card A", content="Alpha"),
            KnowledgeCardMatch(node_id=2, current_version=3, title="Card B", content="Beta"),
        ]

    async def search_vector_candidates(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[VectorSearchCandidate]:
        assert query_embedding
        self.vector_candidate_limits.append(limit)
        assert self.vector_candidates is not None
        return self.vector_candidates

    async def search_lexical_candidates(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> list[LexicalSearchCandidate]:
        assert query_text == "quantum mechanics"
        self.lexical_candidate_limits.append(limit)
        assert self.lexical_candidates is not None
        return self.lexical_candidates

    async def fetch_connected_title_candidates(
        self,
        *,
        matched_node_ids: Sequence[int],
    ) -> list[ConnectedTitleCandidate]:
        assert matched_node_ids == [1, 2]
        return [
            ConnectedTitleCandidate(node_id=3, title="Card C"),
            ConnectedTitleCandidate(node_id=3, title="Card C (duplicate)"),
            ConnectedTitleCandidate(node_id=4, title="Card A"),
            ConnectedTitleCandidate(node_id=5, title="Card D"),
        ]

    async def fetch_projection_edges_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionEdge]:
        sorted_node_ids = sorted(set(node_ids))
        if len(sorted_node_ids) < 2:
            return []

        return [
            ProjectionEdge(
                node_a_id=sorted_node_ids[0],
                node_b_id=sorted_node_ids[1],
                strength=0.88,
            )
        ]

    async def fetch_projection_cards_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionCardNode]:
        return [
            ProjectionCardNode(
                node_id=node_id,
                current_version=1,
                title=f"Card {node_id}",
                content=f"Content {node_id}",
            )
            for node_id in sorted(set(node_ids))
        ]

    async def fetch_projection_card_titles_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionCardTitle]:
        return [
            ProjectionCardTitle(
                node_id=node_id,
                title=f"Card {node_id}",
            )
            for node_id in sorted(set(node_ids))
        ]

    async def fetch_projection_edges_touching_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionEdge]:
        return await self.fetch_projection_edges_for_node_ids(node_ids=node_ids)

    async def fetch_projection_edges_for_edge_ids(
        self,
        *,
        edge_ids: Sequence[int],
    ) -> list[ProjectionEdge]:
        return [
            ProjectionEdge(
                node_a_id=edge_id,
                node_b_id=edge_id + 100,
                strength=0.88,
            )
            for edge_id in sorted(set(edge_ids))
        ]

    async def fetch_adjacent_edge_ids_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[int]:
        return [700 + node_id for node_id in sorted(set(node_ids))]

    async def fetch_unassigned_nodes_for_taxonomy_classification(
        self,
        *,
        limit: int | None,
    ) -> list[TaxonomyClassificationNodeInput]:
        assert limit is None or limit >= 0
        return []

    async def create_node(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        assert self.created_nodes is not None
        self.created_nodes.append((title, content, embedding))
        return 99

    async def fetch_card_version(
        self,
        *,
        node_id: int,
        version: int,
    ) -> CardVersionSnapshot | None:
        assert self.card_versions_by_key is not None
        return self.card_versions_by_key.get((node_id, version))

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
        assert self.created_suggested_edits is not None
        self.created_suggested_edits.append(
            (
                node_id,
                base_version,
                suggested_title,
                suggested_content,
                suggested_by_user_id,
                reason,
            )
        )
        record = CardSuggestedEditRecord(
            id=self.next_suggested_edit_id,
            node_id=node_id,
            base_version=base_version,
            suggested_title=suggested_title,
            suggested_content=suggested_content,
            suggested_by_user_id=suggested_by_user_id,
            status="pending",
            created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
        )
        self.next_suggested_edit_id += 1
        return record

    async def create_card_proposal(
        self,
        *,
        proposal_type: str,
        submitted_by_user_id: str,
        reason: str,
        payload: dict[str, object],
    ) -> CardProposalRecord:
        raise AssertionError("Proposal writes are not expected in this test.")

    async def fetch_card_proposal(self, *, proposal_id: int) -> CardProposalRecord | None:
        raise AssertionError("Proposal reads are not expected in this test.")

    async def list_card_proposals_for_user(self, *, user_id: str) -> list[CardProposalRecord]:
        raise AssertionError("Proposal lists are not expected in this test.")

    async def list_pending_card_proposals(self) -> list[CardProposalRecord]:
        raise AssertionError("Proposal review lists are not expected in this test.")

    async def has_active_workspace_review_role(self, *, user_id: str) -> bool:
        raise AssertionError("Reviewer role checks are not expected in this test.")

    async def create_next_card_version(
        self,
        *,
        node_id: int,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        raise AssertionError("Proposal apply writes are not expected in this test.")

    async def archive_node(self, *, node_id: int) -> None:
        raise AssertionError("Proposal archive writes are not expected in this test.")

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
        raise AssertionError("Proposal acceptance is not expected in this test.")

    async def mark_card_proposal_rejected(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
    ) -> CardProposalRecord:
        raise AssertionError("Proposal rejection is not expected in this test.")

    async def mark_card_proposal_withdrawn(
        self,
        *,
        proposal_id: int,
    ) -> CardProposalRecord:
        raise AssertionError("Proposal withdrawal is not expected in this test.")

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
        raise AssertionError("Proposal audits are not expected in this test.")

    async def search_similarity_candidates(
        self,
        *,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
        limit: int,
    ) -> list[SimilarNodeCandidate]:
        assert query_embedding == [0.3, 0.2, 0.1]
        self.semantic_excluded_node_ids.append(list(excluded_node_ids))
        self.semantic_candidate_limits.append(limit)
        if self.semantic_candidates is not None:
            return list(self.semantic_candidates)
        return [
            SimilarNodeCandidate(node_id=4, similarity=0.91),
            SimilarNodeCandidate(node_id=8, similarity=0.49),
            SimilarNodeCandidate(node_id=11, similarity=0.5),
        ]

    async def search_title_mention_candidates(
        self,
        *,
        content: str,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
        limit: int,
    ) -> list[SimilarNodeCandidate]:
        assert content
        assert query_embedding == [0.3, 0.2, 0.1]
        assert excluded_node_ids == [99]
        self.title_mention_limits.append(limit)
        return list(self.title_mention_candidates or [])

    async def create_edge_with_adjacency(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> int:
        assert self.created_edges is not None
        if self.fail_on_edge_for_node_id == related_node_id:
            raise RuntimeError("edge insert failed")
        self.created_edges.append((source_node_id, related_node_id, strength))
        edge_id = self.next_edge_id
        self.next_edge_id += 1
        return edge_id

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@dataclass(slots=True)
class _ProposalRepo:
    card_versions_by_key: dict[tuple[int, int], CardVersionSnapshot] = field(default_factory=dict)
    proposals_by_id: dict[int, CardProposalRecord] = field(default_factory=dict)
    reviewer_user_ids: set[str] = field(default_factory=set)
    created_proposals: list[tuple[CardProposalType, str, str, dict[str, object]]] = field(
        default_factory=list
    )
    accepted_proposals: list[
        tuple[int, str, str | None, list[int], list[dict[str, int]], dict[str, object] | None]
    ] = field(default_factory=list)
    created_audits: list[
        tuple[int, str, str, list[int], list[dict[str, int]], dict[str, object] | None, str | None]
    ] = field(default_factory=list)
    updated_versions: list[tuple[int, str, str, list[float]]] = field(default_factory=list)
    archived_nodes: list[int] = field(default_factory=list)
    next_proposal_id: int = 900
    committed: bool = False
    rolled_back: bool = False

    async def fetch_card_version(
        self,
        *,
        node_id: int,
        version: int,
    ) -> CardVersionSnapshot | None:
        return self.card_versions_by_key.get((node_id, version))

    async def create_card_proposal(
        self,
        *,
        proposal_type: CardProposalType,
        submitted_by_user_id: str,
        reason: str,
        payload: dict[str, object],
    ) -> CardProposalRecord:
        self.created_proposals.append((proposal_type, submitted_by_user_id, reason, payload))
        record = CardProposalRecord(
            id=self.next_proposal_id,
            proposal_type=proposal_type,
            reason=reason,
            status="pending_review",
            submitted_by_user_id=submitted_by_user_id,
            reviewed_by_user_id=None,
            review_note=None,
            payload=payload,
            created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
            reviewed_at=None,
        )
        self.next_proposal_id += 1
        self.proposals_by_id[record.id] = record
        return record

    async def fetch_card_proposal(self, *, proposal_id: int) -> CardProposalRecord | None:
        return self.proposals_by_id.get(proposal_id)

    async def list_card_proposals_for_user(self, *, user_id: str) -> list[CardProposalRecord]:
        return [
            proposal
            for proposal in self.proposals_by_id.values()
            if proposal.submitted_by_user_id == user_id
        ]

    async def list_pending_card_proposals(self) -> list[CardProposalRecord]:
        return [
            proposal
            for proposal in self.proposals_by_id.values()
            if proposal.status == "pending_review"
        ]

    async def has_active_workspace_review_role(self, *, user_id: str) -> bool:
        return user_id in self.reviewer_user_ids

    async def create_next_card_version(
        self,
        *,
        node_id: int,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        self.updated_versions.append((node_id, title, content, embedding))
        return 4

    async def archive_node(self, *, node_id: int) -> None:
        self.archived_nodes.append(node_id)

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
        self.accepted_proposals.append(
            (
                proposal_id,
                reviewer_user_id,
                review_note,
                affected_node_ids,
                created_versions,
                archive_outcome,
            )
        )
        record = self.proposals_by_id[proposal_id].model_copy(
            update={
                "status": "accepted_applied",
                "reviewed_by_user_id": reviewer_user_id,
                "review_note": review_note,
                "reviewed_at": datetime(2026, 4, 28, 19, 0, tzinfo=UTC),
            }
        )
        self.proposals_by_id[proposal_id] = record
        return record

    async def mark_card_proposal_rejected(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
    ) -> CardProposalRecord:
        record = self.proposals_by_id[proposal_id].model_copy(
            update={
                "status": "rejected",
                "reviewed_by_user_id": reviewer_user_id,
                "review_note": review_note,
                "reviewed_at": datetime(2026, 4, 28, 19, 0, tzinfo=UTC),
            }
        )
        self.proposals_by_id[proposal_id] = record
        return record

    async def mark_card_proposal_withdrawn(
        self,
        *,
        proposal_id: int,
    ) -> CardProposalRecord:
        record = self.proposals_by_id[proposal_id].model_copy(update={"status": "withdrawn"})
        self.proposals_by_id[proposal_id] = record
        return record

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
        self.created_audits.append(
            (
                proposal_id,
                reviewer_user_id,
                proposal_type,
                affected_node_ids,
                created_versions,
                archive_outcome,
                review_note,
            )
        )

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _ProposalEmbeddingClient:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def embed_text(self, text: str) -> list[float]:
        self.texts.append(text)
        return [0.4, 0.3, 0.2]


def _proposal_service(
    repo: _ProposalRepo,
    embedding_client: _ProposalEmbeddingClient | None = None,
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        repo=cast(KnowledgeGraphRepoProtocol, repo),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=0,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=0,
        embedding_client=embedding_client,
    )


@dataclass(slots=True)
class _StubTaxonomyProjectionPort:
    scope_lookup_by_node_id: dict[int, TaxonomyScopeIdentity]
    root_taxonomy_node_id: int = 1
    add_calls: list[tuple[TaxonomyScopeIdentity, list[int]]] = None  # type: ignore[assignment]
    root_assignment_calls: list[int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.add_calls is None:
            self.add_calls = []
        if self.root_assignment_calls is None:
            self.root_assignment_calls = []

    async def list_scope_identities_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, TaxonomyScopeIdentity]:
        return {
            node_id: self.scope_lookup_by_node_id[node_id]
            for node_id in node_ids
            if node_id in self.scope_lookup_by_node_id
        }

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None:
        self.add_calls.append((scope_identity, list(edge_ids)))

    async def assign_node_to_root(self, *, node_id: int) -> int:
        self.root_assignment_calls.append(node_id)
        return self.root_taxonomy_node_id


@pytest.mark.anyio
async def test_search_searchable_cards_returns_records_with_node_id_title_content() -> None:
    repo = _StubRepo(
        vector_candidates=[
            VectorSearchCandidate(
                node_id=1,
                current_version=1,
                title="Card A",
                content="Alpha",
                vector_rank=1,
            ),
            VectorSearchCandidate(
                node_id=2,
                current_version=3,
                title="Card B",
                content="Beta",
                vector_rank=2,
            ),
        ],
        lexical_candidates=[],
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )
    result = await service.search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=[0.1] * 8,
        limit=5,
        vector_candidate_limit=64,
    )

    records = result.matches
    assert result.vector_candidate_count == 2
    assert repo.vector_candidate_limits == [64]
    assert repo.lexical_candidate_limits == [5]
    assert len(records) == 2
    assert records[0].node_id == 1
    assert records[0].current_version == 1
    assert records[0].title == "Card A"
    assert records[0].content == "Alpha"


@pytest.mark.anyio
async def test_search_searchable_cards_rejects_vector_candidate_limit_below_final_limit() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(
            vector_candidates=[
                VectorSearchCandidate(
                    node_id=1,
                    current_version=1,
                    title="Card A",
                    content="Alpha",
                    vector_rank=1,
                ),
                VectorSearchCandidate(
                    node_id=2,
                    current_version=3,
                    title="Card B",
                    content="Beta",
                    vector_rank=2,
                ),
            ],
            lexical_candidates=[],
        ),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )
    with pytest.raises(ValueError, match="vector_candidate_limit"):
        await service.search_searchable_cards(
            query_text="quantum mechanics",
            query_embedding=[0.1] * 8,
            limit=5,
            vector_candidate_limit=4,
        )


@pytest.mark.anyio
async def test_search_searchable_cards_prioritizes_title_matches_over_content_only() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(
            vector_candidates=[
                VectorSearchCandidate(
                    node_id=2,
                    current_version=1,
                    title="Content Only",
                    content="Quantum mechanics appears in the body.",
                    vector_rank=1,
                ),
                VectorSearchCandidate(
                    node_id=4,
                    current_version=1,
                    title="Semantic Neighbor",
                    content="Vector-only result.",
                    vector_rank=2,
                ),
                VectorSearchCandidate(
                    node_id=1,
                    current_version=1,
                    title="Quantum Mechanics",
                    content="Exact title result.",
                    vector_rank=3,
                ),
            ],
            lexical_candidates=[
                LexicalSearchCandidate(
                    node_id=2,
                    current_version=1,
                    title="Content Only",
                    content="Quantum mechanics appears in the body.",
                    lexical_rank=1,
                    lexical_score=0.9,
                    exact_title_match=False,
                    title_phrase_match=False,
                    title_all_tokens_match=False,
                ),
                LexicalSearchCandidate(
                    node_id=1,
                    current_version=1,
                    title="Quantum Mechanics",
                    content="Exact title result.",
                    lexical_rank=2,
                    lexical_score=0.5,
                    exact_title_match=True,
                    title_phrase_match=True,
                    title_all_tokens_match=True,
                ),
                LexicalSearchCandidate(
                    node_id=3,
                    current_version=1,
                    title="Mechanics Quantum Notes",
                    content="All tokens appear in the title.",
                    lexical_rank=3,
                    lexical_score=0.4,
                    exact_title_match=False,
                    title_phrase_match=False,
                    title_all_tokens_match=True,
                ),
            ],
        ),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    result = await service.search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=[0.1] * 8,
        limit=5,
        vector_candidate_limit=64,
    )

    assert [record.node_id for record in result.matches] == [1, 3, 2, 4]
    assert result.vector_candidate_count == 3


@pytest.mark.anyio
async def test_search_searchable_cards_preserves_vector_only_fallback() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(
            vector_candidates=[
                VectorSearchCandidate(
                    node_id=8,
                    current_version=1,
                    title="Semantic Recall",
                    content="No lexical hit.",
                    vector_rank=1,
                )
            ],
            lexical_candidates=[],
        ),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    result = await service.search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=[0.1] * 8,
        limit=5,
        vector_candidate_limit=64,
    )

    assert [record.node_id for record in result.matches] == [8]
    assert result.vector_candidate_count == 1


@pytest.mark.anyio
async def test_submit_card_suggested_edit_stores_pending_suggestion_against_base_version() -> None:
    repo = _StubRepo(
        card_versions_by_key={
            (1, 2): CardVersionSnapshot(
                node_id=1,
                version=2,
                title="Old title",
                content="Old content",
            )
        },
        created_suggested_edits=[],
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    record = await service.submit_card_suggested_edit(
        node_id=1,
        base_version=2,
        suggested_title="Better title",
        suggested_content="Better content",
        suggested_by_user_id="logto-user-123",
        reason="The current card needs clearer wording.",
    )

    assert record.id == 700
    assert record.status == "pending"
    assert repo.created_suggested_edits == [
        (
            1,
            2,
            "Better title",
            "Better content",
            "logto-user-123",
            "The current card needs clearer wording.",
        )
    ]
    assert repo.committed is True
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_submit_card_suggested_edit_rejects_unknown_base_version() -> None:
    repo = _StubRepo(card_versions_by_key={}, created_suggested_edits=[])
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    with pytest.raises(CardVersionNotFoundError):
        await service.submit_card_suggested_edit(
            node_id=1,
            base_version=9,
            suggested_title="Better title",
            suggested_content="Better content",
            suggested_by_user_id="logto-user-123",
            reason="The current card needs clearer wording.",
        )

    assert repo.created_suggested_edits == []
    assert repo.committed is False
    assert repo.rolled_back is True


@pytest.mark.anyio
async def test_submit_card_suggested_edit_rejects_noop_against_base_version() -> None:
    repo = _StubRepo(
        card_versions_by_key={
            (1, 1): CardVersionSnapshot(
                node_id=1,
                version=1,
                title="Same title",
                content="Same content",
            )
        },
        created_suggested_edits=[],
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    with pytest.raises(CardSuggestedEditNoChangeError):
        await service.submit_card_suggested_edit(
            node_id=1,
            base_version=1,
            suggested_title="Same title",
            suggested_content="Same content",
            suggested_by_user_id="logto-user-123",
            reason="The current card needs clearer wording.",
        )

    assert repo.created_suggested_edits == []
    assert repo.committed is False
    assert repo.rolled_back is True


@pytest.mark.anyio
async def test_submit_card_suggested_edit_accepts_stale_existing_base_version() -> None:
    repo = _StubRepo(
        card_versions_by_key={
            (1, 1): CardVersionSnapshot(
                node_id=1,
                version=1,
                title="Version one title",
                content="Version one content",
            )
        },
        created_suggested_edits=[],
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    record = await service.submit_card_suggested_edit(
        node_id=1,
        base_version=1,
        suggested_title="Better title",
        suggested_content="Version one content",
        suggested_by_user_id="logto-user-123",
        reason="The current card needs clearer wording.",
    )

    assert record.base_version == 1
    assert repo.created_suggested_edits == [
        (
            1,
            1,
            "Better title",
            "Version one content",
            "logto-user-123",
            "The current card needs clearer wording.",
        )
    ]


@pytest.mark.anyio
async def test_get_connected_titles_dedups_by_node_id_and_excludes_titles() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )
    titles = await service.get_connected_titles(
        matched_node_ids=[1, 2],
        excluded_titles={"Card A"},
        limit=10,
    )

    assert titles == ["Card C", "Card D"]


@pytest.mark.anyio
async def test_list_projection_edges_for_node_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    records = await service.list_projection_edges_for_node_ids(node_ids=[3, 1, 2])

    assert [record.model_dump() for record in records] == [
        {"node_a_id": 1, "node_b_id": 2, "strength": 0.88}
    ]


@pytest.mark.anyio
async def test_list_projection_edges_touching_node_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    records = await service.list_projection_edges_touching_node_ids(node_ids=[3, 1, 2])

    assert [record.model_dump() for record in records] == [
        {"node_a_id": 1, "node_b_id": 2, "strength": 0.88}
    ]


@pytest.mark.anyio
async def test_list_projection_edges_for_edge_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    records = await service.list_projection_edges_for_edge_ids(edge_ids=[9, 3])

    assert [record.model_dump() for record in records] == [
        {"node_a_id": 3, "node_b_id": 103, "strength": 0.88},
        {"node_a_id": 9, "node_b_id": 109, "strength": 0.88},
    ]


@pytest.mark.anyio
async def test_list_projection_card_titles_for_node_ids_omits_content() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    records = await service.list_projection_card_titles_for_node_ids(node_ids=[9, 3, 9])

    assert [record.model_dump() for record in records] == [
        {"node_id": 3, "title": "Card 3"},
        {"node_id": 9, "title": "Card 9"},
    ]


@pytest.mark.anyio
async def test_list_adjacent_edge_ids_for_node_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
    )

    edge_ids = await service.list_adjacent_edge_ids_for_node_ids(node_ids=[8, 2, 8])

    assert edge_ids == [702, 708]


@pytest.mark.anyio
async def test_materialize_card_from_ingestion_uses_configured_title_mention_budget() -> None:
    repo = _StubRepo(
        created_nodes=[],
        created_edges=[],
        title_mention_candidates=[
            SimilarNodeCandidate(node_id=4, similarity=0.95),
            SimilarNodeCandidate(node_id=11, similarity=0.9),
            SimilarNodeCandidate(node_id=18, similarity=0.85),
        ],
        semantic_candidates=[],
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=2,
        edge_semantic_top_k=0,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=5,
    )

    await service.materialize_card_from_ingestion(
        title="Card X",
        content="Gamma references several existing card titles.",
        embedding=[0.3, 0.2, 0.1],
    )

    assert repo.title_mention_limits == [2]
    assert repo.created_edges == [
        (99, 4, 0.95),
        (99, 11, 0.9),
    ]
    assert repo.semantic_candidate_limits == []


@pytest.mark.anyio
async def test_materialize_card_from_ingestion_uses_configured_semantic_budget_and_limit() -> None:
    repo = _StubRepo(
        created_nodes=[],
        created_edges=[],
        title_mention_candidates=[SimilarNodeCandidate(node_id=4, similarity=0.95)],
        semantic_candidates=[
            SimilarNodeCandidate(node_id=11, similarity=0.91),
            SimilarNodeCandidate(node_id=18, similarity=0.8),
            SimilarNodeCandidate(node_id=20, similarity=0.79),
        ],
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=1,
        edge_semantic_top_k=2,
        edge_semantic_min_strength=0.8,
        edge_semantic_candidate_limit=7,
    )

    await service.materialize_card_from_ingestion(
        title="Card X",
        content="Gamma references a title and semantic neighbors.",
        embedding=[0.3, 0.2, 0.1],
    )

    assert repo.semantic_candidate_limits == [7]
    assert repo.semantic_excluded_node_ids == [[99, 4]]
    assert repo.created_edges == [
        (99, 4, 0.95),
        (99, 11, 0.91),
        (99, 18, 0.8),
    ]


@pytest.mark.anyio
async def test_materialize_card_from_ingestion_can_disable_each_candidate_pool() -> None:
    repo = _StubRepo(
        created_nodes=[],
        created_edges=[],
        title_mention_candidates=[SimilarNodeCandidate(node_id=4, similarity=0.95)],
        semantic_candidates=[SimilarNodeCandidate(node_id=11, similarity=0.91)],
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=0,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=3,
    )

    await service.materialize_card_from_ingestion(
        title="Card X",
        content="Gamma",
        embedding=[0.3, 0.2, 0.1],
    )

    assert repo.title_mention_limits == []
    assert repo.semantic_candidate_limits == []
    assert repo.created_edges == []


@pytest.mark.anyio
async def test_materialize_card_from_ingestion_creates_node_and_threshold_edges() -> None:
    repo = _StubRepo(created_nodes=[], created_edges=[])
    taxonomy_projection_port = _StubTaxonomyProjectionPort(
        scope_lookup_by_node_id={
            99: TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=1),
            4: TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=8),
            11: TaxonomyScopeIdentity(scope_kind="virtual_unclassified", taxonomy_node_id=4),
        }
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
        taxonomy_projection_port=taxonomy_projection_port,
    )

    node_id = await service.materialize_card_from_ingestion(
        title="Card X",
        content="Gamma",
        embedding=[0.3, 0.2, 0.1],
    )

    assert node_id == 99
    assert repo.created_nodes == [("Card X", "Gamma", [0.3, 0.2, 0.1])]
    assert taxonomy_projection_port.root_assignment_calls == [99]
    assert repo.created_edges == [
        (99, 4, 0.91),
        (99, 11, 0.5),
    ]
    assert taxonomy_projection_port.add_calls == [
        (TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=1), [500]),
        (TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=8), [500]),
        (TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=1), [501]),
        (TaxonomyScopeIdentity(scope_kind="virtual_unclassified", taxonomy_node_id=4), [501]),
    ]
    assert repo.committed is True
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_submit_edit_card_proposal_stores_unified_pending_payload() -> None:
    repo = _ProposalRepo(
        card_versions_by_key={
            (10, 3): CardVersionSnapshot(
                node_id=10,
                version=3,
                title="Old title",
                content="Old content",
            )
        }
    )
    service = _proposal_service(repo)

    record = await service.submit_card_proposal(
        proposal_type="edit",
        submitted_by_user_id="logto-user-123",
        target_node_id=10,
        base_version=3,
        suggested_title="Better title",
        suggested_content="Better content",
        reason="The current card needs clearer wording.",
    )

    assert record.status == "pending_review"
    assert repo.created_proposals == [
        (
            "edit",
            "logto-user-123",
            "The current card needs clearer wording.",
            {
                "target_node_id": 10,
                "base_version": 3,
                "suggested_title": "Better title",
                "suggested_content": "Better content",
            },
        )
    ]
    assert repo.committed is True


@pytest.mark.anyio
async def test_submit_delete_card_proposal_stores_target_card_content() -> None:
    repo = _ProposalRepo(
        card_versions_by_key={
            (10, 3): CardVersionSnapshot(
                node_id=10,
                version=3,
                title="Physics",
                content="Physics studies matter, motion, energy, and force.",
            )
        }
    )
    service = _proposal_service(repo)

    record = await service.submit_card_proposal(
        proposal_type="delete",
        submitted_by_user_id="logto-user-123",
        target_node_id=10,
        base_version=3,
        reason="Duplicate card.",
    )

    assert record.status == "pending_review"
    assert repo.created_proposals == [
        (
            "delete",
            "logto-user-123",
            "Duplicate card.",
            {
                "target_node_id": 10,
                "base_version": 3,
                "target_title": "Physics",
                "target_content": "Physics studies matter, motion, energy, and force.",
            },
        )
    ]
    assert repo.committed is True


@pytest.mark.anyio
async def test_submit_card_proposal_requires_common_reason() -> None:
    repo = _ProposalRepo(
        card_versions_by_key={
            (10, 3): CardVersionSnapshot(
                node_id=10,
                version=3,
                title="Old title",
                content="Old content",
            )
        }
    )
    service = _proposal_service(repo)

    with pytest.raises(CardProposalValidationError, match="reason"):
        await service.submit_card_proposal(
            proposal_type="edit",
            submitted_by_user_id="logto-user-123",
            reason=" ",
            target_node_id=10,
            base_version=3,
            suggested_title="Better title",
            suggested_content="Better content",
        )

    assert repo.created_proposals == []
    assert repo.rolled_back is True


@pytest.mark.anyio
async def test_accept_edit_card_proposal_requires_reviewer_role() -> None:
    repo = _ProposalRepo(
        proposals_by_id={
            900: CardProposalRecord(
                id=900,
                proposal_type="edit",
                reason="The current card needs clearer wording.",
                status="pending_review",
                submitted_by_user_id="contributor",
                reviewed_by_user_id=None,
                review_note=None,
                payload={
                    "target_node_id": 10,
                    "base_version": 3,
                    "suggested_title": "Better title",
                    "suggested_content": "Better content",
                },
                created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
                updated_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
                reviewed_at=None,
            )
        }
    )
    service = _proposal_service(repo, _ProposalEmbeddingClient())

    with pytest.raises(CardProposalPermissionError):
        await service.accept_card_proposal(
            proposal_id=900,
            reviewer_user_id="ordinary-user",
            review_note="Looks good.",
        )

    assert repo.accepted_proposals == []
    assert repo.rolled_back is True


@pytest.mark.anyio
async def test_accept_edit_card_proposal_applies_version_and_audit_atomically() -> None:
    embedding_client = _ProposalEmbeddingClient()
    repo = _ProposalRepo(
        proposals_by_id={
            900: CardProposalRecord(
                id=900,
                proposal_type="edit",
                reason="The current card needs clearer wording.",
                status="pending_review",
                submitted_by_user_id="contributor",
                reviewed_by_user_id=None,
                review_note=None,
                payload={
                    "target_node_id": 10,
                    "base_version": 3,
                    "suggested_title": "Better title",
                    "suggested_content": "Better content",
                },
                created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
                updated_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
                reviewed_at=None,
            )
        },
        reviewer_user_ids={"reviewer"},
    )
    service = _proposal_service(repo, embedding_client)

    record = await service.accept_card_proposal(
        proposal_id=900,
        reviewer_user_id="reviewer",
        review_note="Looks good.",
    )

    assert record.status == "accepted_applied"
    assert embedding_client.texts == ["Better title\n\nBetter content"]
    assert repo.updated_versions == [(10, "Better title", "Better content", [0.4, 0.3, 0.2])]
    assert repo.accepted_proposals == [
        (900, "reviewer", "Looks good.", [10], [{"node_id": 10, "version": 4}], None)
    ]
    assert repo.created_audits == [
        (900, "reviewer", "edit", [10], [{"node_id": 10, "version": 4}], None, "Looks good.")
    ]
    assert repo.committed is True


@pytest.mark.anyio
async def test_accept_delete_card_proposal_archives_node_and_records_outcome() -> None:
    repo = _ProposalRepo(
        proposals_by_id={
            901: CardProposalRecord(
                id=901,
                proposal_type="delete",
                reason="Duplicate card",
                status="pending_review",
                submitted_by_user_id="contributor",
                reviewed_by_user_id=None,
                review_note=None,
                payload={
                    "target_node_id": 11,
                    "base_version": 2,
                    "target_title": "Physics",
                    "target_content": "Duplicate physics card.",
                },
                created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
                updated_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
                reviewed_at=None,
            )
        },
        reviewer_user_ids={"reviewer"},
    )
    service = _proposal_service(repo, _ProposalEmbeddingClient())

    record = await service.accept_card_proposal(
        proposal_id=901,
        reviewer_user_id="reviewer",
        review_note="Archive duplicate.",
    )

    assert record.status == "accepted_applied"
    assert repo.archived_nodes == [11]
    assert repo.accepted_proposals == [
        (
            901,
            "reviewer",
            "Archive duplicate.",
            [11],
            [],
            {"archived_node_id": 11},
        )
    ]
    assert repo.created_audits == [
        (
            901,
            "reviewer",
            "delete",
            [11],
            [],
            {"archived_node_id": 11},
            "Archive duplicate.",
        )
    ]


@pytest.mark.anyio
async def test_materialize_card_from_ingestion_rolls_back_and_reraises() -> None:
    repo = _StubRepo(
        created_nodes=[],
        created_edges=[],
        fail_on_edge_for_node_id=11,
    )
    taxonomy_projection_port = _StubTaxonomyProjectionPort(
        scope_lookup_by_node_id={
            99: TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=1),
            4: TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=8),
            11: TaxonomyScopeIdentity(scope_kind="virtual_unclassified", taxonomy_node_id=4),
        }
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_title_mention_top_k=0,
        edge_semantic_top_k=10,
        edge_semantic_min_strength=0.5,
        edge_semantic_candidate_limit=10,
        taxonomy_projection_port=taxonomy_projection_port,
    )

    with pytest.raises(RuntimeError, match="edge insert failed"):
        await service.materialize_card_from_ingestion(
            title="Card X",
            content="Gamma",
            embedding=[0.3, 0.2, 0.1],
        )

    assert repo.committed is False
    assert repo.rolled_back is True
    assert taxonomy_projection_port.root_assignment_calls == [99]
    assert taxonomy_projection_port.add_calls == [
        (TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=1), [500]),
        (TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=8), [500]),
    ]
