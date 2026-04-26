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
    ProjectionCardNode,
    ProjectionEdge,
    SimilarNodeCandidate,
    TaxonomyClassificationNodeInput,
)
from modules.knowledge_graph.service import KnowledgeGraphService


@dataclass(slots=True)
class _StubRepo:
    created_nodes: list[tuple[str, str, list[float]]] | None = None
    created_edges: list[tuple[int, int, float]] | None = None
    next_edge_id: int = 500
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
                title=f"Card {node_id}",
                content=f"Content {node_id}",
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
    leaf_lookup_by_node_id: dict[int, int]
    add_calls: list[tuple[int, list[int]]] = None  # type: ignore[assignment]
    root_assignment_calls: list[int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.add_calls is None:
            self.add_calls = []
        if self.root_assignment_calls is None:
            self.root_assignment_calls = []

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        return {
            node_id: self.leaf_lookup_by_node_id[node_id]
            for node_id in node_ids
            if node_id in self.leaf_lookup_by_node_id
        }

    async def add_projected_edge_ids_for_leaf(self, *, leaf_id: int, edge_ids: list[int]) -> None:
        self.add_calls.append((leaf_id, list(edge_ids)))

    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int:
        self.root_assignment_calls.append(node_id)
        return self.leaf_lookup_by_node_id[node_id]


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
async def test_list_projection_edges_for_node_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    records = await service.list_projection_edges_for_node_ids(node_ids=[3, 1, 2])

    assert [record.model_dump() for record in records] == [
        {"node_a_id": 1, "node_b_id": 2, "strength": 0.88}
    ]


@pytest.mark.anyio
async def test_list_projection_edges_touching_node_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    records = await service.list_projection_edges_touching_node_ids(node_ids=[3, 1, 2])

    assert [record.model_dump() for record in records] == [
        {"node_a_id": 1, "node_b_id": 2, "strength": 0.88}
    ]


@pytest.mark.anyio
async def test_list_projection_edges_for_edge_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    records = await service.list_projection_edges_for_edge_ids(edge_ids=[9, 3])

    assert [record.model_dump() for record in records] == [
        {"node_a_id": 3, "node_b_id": 103, "strength": 0.88},
        {"node_a_id": 9, "node_b_id": 109, "strength": 0.88},
    ]


@pytest.mark.anyio
async def test_list_adjacent_edge_ids_for_node_ids() -> None:
    service = KnowledgeGraphService(
        repo=_StubRepo(),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
    )

    edge_ids = await service.list_adjacent_edge_ids_for_node_ids(node_ids=[8, 2, 8])

    assert edge_ids == [702, 708]


@pytest.mark.anyio
async def test_materialize_card_from_ingestion_creates_node_and_threshold_edges() -> None:
    repo = _StubRepo(created_nodes=[], created_edges=[])
    taxonomy_projection_port = _StubTaxonomyProjectionPort(
        leaf_lookup_by_node_id={99: 4, 4: 8, 11: 4}
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
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
        (4, [500]),
        (8, [500]),
        (4, [501]),
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
        leaf_lookup_by_node_id={99: 4, 4: 8, 11: 4}
    )
    service = KnowledgeGraphService(
        repo=repo,
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.5,
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
        (4, [500]),
        (8, [500]),
    ]
