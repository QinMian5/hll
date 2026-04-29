"""
Abstract: Deterministic rebuild orchestration for knowledge-graph similarity edges.
Out of scope: CLI wiring, transaction commits, and taxonomy projection rebuilding.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from modules.knowledge_graph.dto import SimilarNodeCandidate


@dataclass(slots=True, frozen=True)
class PlannedEdge:
    source_node_id: int
    related_node_id: int
    strength: float


@dataclass(slots=True, frozen=True)
class RebuildNodeEmbedding:
    node_id: int
    embedding: Sequence[float]


@dataclass(slots=True, frozen=True)
class EdgeRebuildResult:
    edge_semantic_top_k: int
    edge_semantic_min_strength: float
    node_count: int
    planned_edge_count: int
    inserted_edge_count: int
    applied: bool


class EdgeRebuildRepoProtocol(Protocol):
    async def fetch_node_ids_in_rebuild_order(self) -> list[int]: ...

    async def search_historical_similarity_candidates(
        self,
        *,
        source_node_id: int,
    ) -> list[SimilarNodeCandidate]: ...

    async def clear_edges_with_adjacency(self) -> None: ...

    async def create_edge_with_adjacency(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> int: ...


class EdgeRebuildBulkRepoProtocol(Protocol):
    async def fetch_rebuild_nodes_with_embeddings(self) -> list[RebuildNodeEmbedding]: ...

    async def replace_edges_with_adjacency(
        self,
        *,
        planned_edges: Sequence[PlannedEdge],
    ) -> int: ...


def _validate_rebuild_policy(
    *,
    edge_semantic_top_k: int,
    edge_semantic_min_strength: float,
) -> None:
    if edge_semantic_top_k < 1:
        raise ValueError("edge_semantic_top_k must be at least 1.")
    if edge_semantic_min_strength < 0.0 or edge_semantic_min_strength > 1.0:
        raise ValueError("edge_semantic_min_strength must be between 0.0 and 1.0.")


def _validate_chunk_size(*, chunk_size: int) -> None:
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1.")


def plan_knowledge_graph_edges_from_embeddings(
    *,
    nodes: Sequence[RebuildNodeEmbedding],
    edge_semantic_top_k: int,
    edge_semantic_min_strength: float,
    chunk_size: int = 256,
) -> list[PlannedEdge]:
    _validate_rebuild_policy(
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
    )
    _validate_chunk_size(chunk_size=chunk_size)
    if not nodes:
        return []

    ordered_nodes = sorted(nodes, key=lambda node: node.node_id)
    node_ids = np.array([node.node_id for node in ordered_nodes], dtype=np.int64)
    embeddings = np.array([node.embedding for node in ordered_nodes], dtype=np.float32)
    planned_edges: list[PlannedEdge] = []

    for start_index in range(0, len(ordered_nodes), chunk_size):
        end_index = min(start_index + chunk_size, len(ordered_nodes))
        dot_products = embeddings[start_index:end_index] @ embeddings[:end_index].T

        for chunk_offset, source_index in enumerate(range(start_index, end_index)):
            if source_index == 0:
                continue

            source_dot_products = dot_products[chunk_offset, :source_index]
            strengths = np.clip((source_dot_products + 1.0) / 2.0, 0.0, 1.0)
            eligible_indices = np.flatnonzero(strengths >= edge_semantic_min_strength)
            if eligible_indices.size == 0:
                continue

            ordered_candidate_offsets = np.lexsort(
                (
                    node_ids[eligible_indices],
                    -strengths[eligible_indices],
                )
            )
            selected_indices = eligible_indices[ordered_candidate_offsets[:edge_semantic_top_k]]
            for related_index in selected_indices:
                planned_edges.append(
                    PlannedEdge(
                        source_node_id=int(node_ids[source_index]),
                        related_node_id=int(node_ids[related_index]),
                        strength=float(strengths[related_index]),
                    )
                )

    return planned_edges


async def plan_knowledge_graph_edges(
    *,
    repo: EdgeRebuildRepoProtocol,
    edge_semantic_top_k: int,
    edge_semantic_min_strength: float,
) -> tuple[int, list[PlannedEdge]]:
    _validate_rebuild_policy(
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
    )

    node_ids = await repo.fetch_node_ids_in_rebuild_order()
    planned_edges: list[PlannedEdge] = []

    for source_node_id in node_ids:
        candidates = await repo.search_historical_similarity_candidates(
            source_node_id=source_node_id,
        )
        threshold_candidates = [
            candidate
            for candidate in candidates
            if candidate.similarity >= edge_semantic_min_strength
        ]
        for candidate in threshold_candidates[:edge_semantic_top_k]:
            planned_edges.append(
                PlannedEdge(
                    source_node_id=source_node_id,
                    related_node_id=candidate.node_id,
                    strength=candidate.similarity,
                )
            )

    return len(node_ids), planned_edges


async def rebuild_knowledge_graph_edges(
    *,
    repo: EdgeRebuildRepoProtocol,
    edge_semantic_top_k: int,
    edge_semantic_min_strength: float,
    apply: bool,
) -> EdgeRebuildResult:
    node_count, planned_edges = await plan_knowledge_graph_edges(
        repo=repo,
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
    )

    if not apply:
        return EdgeRebuildResult(
            edge_semantic_top_k=edge_semantic_top_k,
            edge_semantic_min_strength=edge_semantic_min_strength,
            node_count=node_count,
            planned_edge_count=len(planned_edges),
            inserted_edge_count=0,
            applied=False,
        )

    await repo.clear_edges_with_adjacency()
    inserted_edge_count = 0
    for edge in planned_edges:
        await repo.create_edge_with_adjacency(
            source_node_id=edge.source_node_id,
            related_node_id=edge.related_node_id,
            strength=edge.strength,
        )
        inserted_edge_count += 1

    return EdgeRebuildResult(
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
        node_count=node_count,
        planned_edge_count=len(planned_edges),
        inserted_edge_count=inserted_edge_count,
        applied=True,
    )


async def rebuild_knowledge_graph_edges_bulk(
    *,
    repo: EdgeRebuildBulkRepoProtocol,
    edge_semantic_top_k: int,
    edge_semantic_min_strength: float,
    apply: bool,
) -> EdgeRebuildResult:
    _validate_rebuild_policy(
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
    )
    nodes = await repo.fetch_rebuild_nodes_with_embeddings()
    planned_edges = plan_knowledge_graph_edges_from_embeddings(
        nodes=nodes,
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
    )

    if not apply:
        return EdgeRebuildResult(
            edge_semantic_top_k=edge_semantic_top_k,
            edge_semantic_min_strength=edge_semantic_min_strength,
            node_count=len(nodes),
            planned_edge_count=len(planned_edges),
            inserted_edge_count=0,
            applied=False,
        )

    inserted_edge_count = await repo.replace_edges_with_adjacency(
        planned_edges=planned_edges,
    )
    return EdgeRebuildResult(
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
        node_count=len(nodes),
        planned_edge_count=len(planned_edges),
        inserted_edge_count=inserted_edge_count,
        applied=True,
    )
