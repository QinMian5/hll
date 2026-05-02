"""
Abstract: Unit tests for knowledge-graph service orchestration and response-shaping
rules.
Out of scope: SQL statement correctness and FastAPI route wiring.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from modules.knowledge_graph.dto import (
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
    CardSuggestedEditNoChangeError,
    CardVersionNotFoundError,
    KnowledgeGraphService,
)
from modules.taxonomy.dto import TaxonomyScopeIdentity


@dataclass(slots=True)
class _StubRepo:
    created_nodes: list[tuple[str, str, list[float]]] | None = None
    created_edges: list[tuple[int, int, float]] | None = None
    card_versions_by_key: dict[tuple[int, int], CardVersionSnapshot] | None = None
    created_suggested_edits: list[tuple[int, int, str, str, str]] | None = None
    vector_candidates: list[VectorSearchCandidate] | None = None
    lexical_candidates: list[LexicalSearchCandidate] | None = None
    title_mention_candidates: list[SimilarNodeCandidate] | None = None
    semantic_candidates: list[SimilarNodeCandidate] | None = None
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
        assert limit == 5
        assert self.vector_candidates is not None
        return self.vector_candidates

    async def search_lexical_candidates(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> list[LexicalSearchCandidate]:
        assert query_text == "quantum mechanics"
        assert limit == 5
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
    ) -> CardSuggestedEditRecord:
        assert self.created_suggested_edits is not None
        self.created_suggested_edits.append(
            (node_id, base_version, suggested_title, suggested_content, suggested_by_user_id)
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
    records = await service.search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=[0.1] * 8,
        limit=5,
    )

    assert len(records) == 2
    assert records[0].node_id == 1
    assert records[0].current_version == 1
    assert records[0].title == "Card A"
    assert records[0].content == "Alpha"


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

    records = await service.search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=[0.1] * 8,
        limit=5,
    )

    assert [record.node_id for record in records] == [1, 3, 2, 4]


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

    records = await service.search_searchable_cards(
        query_text="quantum mechanics",
        query_embedding=[0.1] * 8,
        limit=5,
    )

    assert [record.node_id for record in records] == [8]


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
    )

    assert record.id == 700
    assert record.status == "pending"
    assert repo.created_suggested_edits == [
        (1, 2, "Better title", "Better content", "logto-user-123")
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
    )

    assert record.base_version == 1
    assert repo.created_suggested_edits == [
        (1, 1, "Better title", "Version one content", "logto-user-123")
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
