"""
Abstract: Unit tests for deterministic knowledge-graph edge rebuild orchestration.
Out of scope: SQL execution, CLI wiring, and taxonomy projection rebuilding.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import pytest

from modules.knowledge_graph.dto import SimilarNodeCandidate
from modules.knowledge_graph.edge_rebuild import (
    PlannedEdge,
    RebuildNodeEmbedding,
    plan_knowledge_graph_edges_from_embeddings,
    rebuild_knowledge_graph_edges,
    rebuild_knowledge_graph_edges_bulk,
)


@dataclass(slots=True)
class _StubRepo:
    node_ids: list[int]
    candidates_by_source_node_id: dict[int, list[SimilarNodeCandidate]]
    candidate_requests: list[int] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    created_edges: list[tuple[int, int, float]] = field(default_factory=list)

    async def fetch_node_ids_in_rebuild_order(self) -> list[int]:
        return list(self.node_ids)

    async def search_historical_similarity_candidates(
        self,
        *,
        source_node_id: int,
    ) -> list[SimilarNodeCandidate]:
        self.candidate_requests.append(source_node_id)
        return list(self.candidates_by_source_node_id.get(source_node_id, []))

    async def clear_edges_with_adjacency(self) -> None:
        self.events.append("clear")

    async def create_edge_with_adjacency(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> int:
        self.events.append(f"create:{source_node_id}:{related_node_id}:{strength}")
        self.created_edges.append((source_node_id, related_node_id, strength))
        return len(self.created_edges)


@dataclass(slots=True)
class _StubBulkRepo:
    nodes: list[RebuildNodeEmbedding]
    inserted_edge_count: int
    events: list[str] = field(default_factory=list)
    inserted_edges: list[PlannedEdge] = field(default_factory=list)

    async def fetch_rebuild_nodes_with_embeddings(self) -> list[RebuildNodeEmbedding]:
        self.events.append("fetch_nodes")
        return list(self.nodes)

    async def replace_edges_with_adjacency(
        self,
        *,
        planned_edges: Sequence[PlannedEdge],
    ) -> int:
        self.events.append("replace_edges")
        self.inserted_edges = list(planned_edges)
        return self.inserted_edge_count


@pytest.mark.anyio
async def test_rebuild_dry_run_plans_thresholded_top_k_edges_without_writes() -> None:
    repo = _StubRepo(
        node_ids=[1, 2, 3, 4],
        candidates_by_source_node_id={
            2: [SimilarNodeCandidate(node_id=1, similarity=0.71)],
            3: [
                SimilarNodeCandidate(node_id=2, similarity=0.69),
                SimilarNodeCandidate(node_id=1, similarity=0.92),
            ],
            4: [
                SimilarNodeCandidate(node_id=3, similarity=0.95),
                SimilarNodeCandidate(node_id=2, similarity=0.94),
                SimilarNodeCandidate(node_id=1, similarity=0.93),
            ],
        },
    )

    result = await rebuild_knowledge_graph_edges(
        repo=repo,
        edge_similarity_top_k=2,
        edge_similarity_min_strength=0.7,
        apply=False,
    )

    assert repo.candidate_requests == [1, 2, 3, 4]
    assert repo.events == []
    assert repo.created_edges == []
    assert result.edge_similarity_top_k == 2
    assert result.edge_similarity_min_strength == 0.7
    assert result.node_count == 4
    assert result.planned_edge_count == 4
    assert result.inserted_edge_count == 0
    assert result.applied is False


@pytest.mark.anyio
async def test_rebuild_apply_clears_existing_edges_before_recreating_plan() -> None:
    repo = _StubRepo(
        node_ids=[1, 2],
        candidates_by_source_node_id={
            2: [SimilarNodeCandidate(node_id=1, similarity=0.7)],
        },
    )

    result = await rebuild_knowledge_graph_edges(
        repo=repo,
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.7,
        apply=True,
    )

    assert repo.events == ["clear", "create:2:1:0.7"]
    assert repo.created_edges == [(2, 1, 0.7)]
    assert result.edge_similarity_top_k == 10
    assert result.edge_similarity_min_strength == 0.7
    assert result.node_count == 2
    assert result.planned_edge_count == 1
    assert result.inserted_edge_count == 1
    assert result.applied is True


@pytest.mark.anyio
async def test_bulk_rebuild_dry_run_fetches_embeddings_without_writes() -> None:
    repo = _StubBulkRepo(
        nodes=[
            RebuildNodeEmbedding(node_id=1, embedding=[1.0, 0.0]),
            RebuildNodeEmbedding(node_id=2, embedding=[0.9, 0.1]),
            RebuildNodeEmbedding(node_id=3, embedding=[0.0, 1.0]),
        ],
        inserted_edge_count=1,
    )

    result = await rebuild_knowledge_graph_edges_bulk(
        repo=repo,
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.7,
        apply=False,
    )

    assert repo.events == ["fetch_nodes"]
    assert repo.inserted_edges == []
    assert result.node_count == 3
    assert result.planned_edge_count == 1
    assert result.inserted_edge_count == 0
    assert result.applied is False


@pytest.mark.anyio
async def test_bulk_rebuild_apply_clears_then_inserts_with_same_policy() -> None:
    repo = _StubBulkRepo(
        nodes=[
            RebuildNodeEmbedding(node_id=1, embedding=[1.0, 0.0]),
            RebuildNodeEmbedding(node_id=2, embedding=[0.9, 0.1]),
            RebuildNodeEmbedding(node_id=3, embedding=[0.0, 1.0]),
        ],
        inserted_edge_count=1,
    )

    result = await rebuild_knowledge_graph_edges_bulk(
        repo=repo,
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.7,
        apply=True,
    )

    assert repo.events == ["fetch_nodes", "replace_edges"]
    assert repo.inserted_edges == [
        PlannedEdge(source_node_id=2, related_node_id=1, strength=0.949999988079071)
    ]
    assert result.node_count == 3
    assert result.planned_edge_count == 1
    assert result.inserted_edge_count == 1
    assert result.applied is True


def test_embedding_planner_matches_historical_threshold_top_k_policy() -> None:
    planned_edges = plan_knowledge_graph_edges_from_embeddings(
        nodes=[
            RebuildNodeEmbedding(node_id=1, embedding=[1.0, 0.0]),
            RebuildNodeEmbedding(node_id=2, embedding=[0.9, 0.1]),
            RebuildNodeEmbedding(node_id=3, embedding=[0.8, 0.2]),
        ],
        edge_similarity_top_k=1,
        edge_similarity_min_strength=0.7,
        chunk_size=2,
    )

    assert planned_edges == [
        PlannedEdge(source_node_id=2, related_node_id=1, strength=0.949999988079071),
        PlannedEdge(source_node_id=3, related_node_id=1, strength=0.8999999761581421),
    ]
