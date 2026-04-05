"""
Abstract: Unit tests for knowledge-graph service orchestration and response-shaping
rules.
Out of scope: SQL statement correctness and FastAPI route wiring.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from modules.knowledge_graph.dto import (
    ConnectedTitleCandidate,
    KnowledgeCardMatch,
    SemanticMapProjectionNode,
    SimilarNodeCandidate,
)
from modules.knowledge_graph.service import KnowledgeGraphService


@dataclass(slots=True)
class _StubRepo:
    created_nodes: list[tuple[str, str, list[float]]] | None = None
    created_edges: list[tuple[int, int, float]] | None = None
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
            KnowledgeCardMatch(node_id=1, title="Card A", content="Alpha"),
            KnowledgeCardMatch(node_id=2, title="Card B", content="Beta"),
        ]

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

    async def fetch_projection_nodes(self) -> list[SemanticMapProjectionNode]:
        return [
            SemanticMapProjectionNode(
                node_id=1,
                title="Card A",
                embedding=[0.6, 0.3, 0.1],
            ),
            SemanticMapProjectionNode(
                node_id=2,
                title="Card B",
                embedding=[0.2, 0.7, 0.1],
            ),
        ]

    async def fetch_projection_nodes_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[SemanticMapProjectionNode]:
        return [
            SemanticMapProjectionNode(
                node_id=node_id,
                title=f"Card {node_id}",
                embedding=[0.1, 0.2, 0.3],
            )
            for node_id in node_ids
        ]

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

    async def search_similarity_candidates(
        self,
        *,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
    ) -> list[SimilarNodeCandidate]:
        assert query_embedding == [0.3, 0.2, 0.1]
        assert excluded_node_ids == [99]
        return [
            SimilarNodeCandidate(node_id=4, similarity=0.91),
            SimilarNodeCandidate(node_id=8, similarity=0.49),
            SimilarNodeCandidate(node_id=11, similarity=0.5),
        ]

    async def create_edge_with_adjacency(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> None:
        assert self.created_edges is not None
        if self.fail_on_edge_for_node_id == related_node_id:
            raise RuntimeError("edge insert failed")
        self.created_edges.append((source_node_id, related_node_id, strength))

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.anyio
async def test_search_searchable_cards_returns_records_with_node_id_title_content() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )
    records = await service.search_searchable_cards(
        query_embedding=[0.1] * 8,
        limit=5,
    )

    assert len(records) == 2
    assert records[0].node_id == 1
    assert records[0].title == "Card A"
    assert records[0].content == "Alpha"


@pytest.mark.anyio
async def test_get_connected_titles_dedups_by_node_id_and_excludes_titles() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )
    titles = await service.get_connected_titles(
        matched_node_ids=[1, 2],
        excluded_titles={"Card A"},
        limit=10,
    )

    assert titles == ["Card C", "Card D"]


@pytest.mark.anyio
async def test_list_projection_nodes_for_semantic_map_returns_repo_records() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    records = await service.list_projection_nodes_for_semantic_map()

    assert [record.model_dump() for record in records] == [
        {
            "node_id": 1,
            "title": "Card A",
            "embedding": [0.6, 0.3, 0.1],
        },
        {
            "node_id": 2,
            "title": "Card B",
            "embedding": [0.2, 0.7, 0.1],
        },
    ]


@pytest.mark.anyio
async def test_list_projection_nodes_for_node_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    records = await service.list_projection_nodes_for_node_ids(node_ids=[3, 1, 2])

    assert [record.model_dump() for record in records] == [
        {"node_id": 3, "title": "Card 3", "embedding": [0.1, 0.2, 0.3]},
        {"node_id": 1, "title": "Card 1", "embedding": [0.1, 0.2, 0.3]},
        {"node_id": 2, "title": "Card 2", "embedding": [0.1, 0.2, 0.3]},
    ]


@pytest.mark.anyio
async def test_materialize_card_from_ingestion_creates_node_and_threshold_edges() -> None:
    repo = _StubRepo(created_nodes=[], created_edges=[])
    service = KnowledgeGraphService(
        repo=repo,
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    node_id = await service.materialize_card_from_ingestion(
        title="Card X",
        content="Gamma",
        embedding=[0.3, 0.2, 0.1],
    )

    assert node_id == 99
    assert repo.created_nodes == [("Card X", "Gamma", [0.3, 0.2, 0.1])]
    assert repo.created_edges == [
        (99, 4, 0.91),
        (99, 11, 0.5),
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
    service = KnowledgeGraphService(
        repo=repo,
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    with pytest.raises(RuntimeError, match="edge insert failed"):
        await service.materialize_card_from_ingestion(
            title="Card X",
            content="Gamma",
            embedding=[0.3, 0.2, 0.1],
        )

    assert repo.committed is False
    assert repo.rolled_back is True
