"""
Abstract: Knowledge-graph domain service for retrieval orchestration and ingestion
materialization rules.
Out of scope: HTTP endpoint concerns, queue transport, and dependency injection.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from modules.knowledge_graph.dto import (
    ConnectedTitleCandidate,
    KnowledgeCardMatch,
    ProjectionCardNode,
    ProjectionEdge,
    SimilarNodeCandidate,
    TaxonomyClassificationNodeInput,
)


class KnowledgeGraphRepoProtocol(Protocol):
    async def search_top_cards_by_cosine(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]: ...

    async def fetch_connected_title_candidates(
        self,
        *,
        matched_node_ids: Sequence[int],
    ) -> list[ConnectedTitleCandidate]: ...

    async def fetch_projection_cards_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionCardNode]: ...

    async def fetch_projection_edges_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionEdge]: ...

    async def fetch_projection_edges_touching_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionEdge]: ...

    async def fetch_projection_edges_for_edge_ids(
        self,
        *,
        edge_ids: Sequence[int],
    ) -> list[ProjectionEdge]: ...

    async def fetch_adjacent_edge_ids_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[int]: ...

    async def fetch_unassigned_nodes_for_taxonomy_classification(
        self,
        *,
        limit: int | None,
    ) -> list[TaxonomyClassificationNodeInput]: ...

    async def create_node(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int: ...

    async def search_similarity_candidates(
        self,
        *,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
    ) -> list[SimilarNodeCandidate]: ...

    async def create_edge_with_adjacency(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> int: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class KnowledgeGraphTaxonomyProjectionPort(Protocol):
    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int: ...

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]: ...

    async def add_projected_edge_ids_for_leaf(
        self,
        *,
        leaf_id: int,
        edge_ids: list[int],
    ) -> None: ...


class KnowledgeGraphService:
    def __init__(
        self,
        *,
        repo: KnowledgeGraphRepoProtocol,
        edge_similarity_top_k: int,
        edge_similarity_min_strength: float,
        taxonomy_projection_port: KnowledgeGraphTaxonomyProjectionPort | None = None,
    ) -> None:
        self._repo = repo
        self._edge_similarity_top_k = edge_similarity_top_k
        self._edge_similarity_min_strength = edge_similarity_min_strength
        self._taxonomy_projection_port = taxonomy_projection_port

    async def search_searchable_cards(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]:
        return await self._repo.search_top_cards_by_cosine(
            query_embedding=query_embedding,
            limit=limit,
        )

    async def get_connected_titles(
        self,
        *,
        matched_node_ids: list[int],
        excluded_titles: set[str],
        limit: int,
    ) -> list[str]:
        if not matched_node_ids or limit <= 0:
            return []

        candidates = await self._repo.fetch_connected_title_candidates(
            matched_node_ids=matched_node_ids,
        )

        seen_node_ids: set[int] = set()
        seen_titles = set(excluded_titles)
        connected_titles: list[str] = []

        for candidate in candidates:
            if candidate.node_id in seen_node_ids:
                continue
            if candidate.title in seen_titles:
                continue

            seen_node_ids.add(candidate.node_id)
            seen_titles.add(candidate.title)
            connected_titles.append(candidate.title)

            if len(connected_titles) >= limit:
                break

        return connected_titles

    async def list_projection_cards_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionCardNode]:
        return await self._repo.fetch_projection_cards_for_node_ids(node_ids=node_ids)

    async def list_projection_edges_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionEdge]:
        return await self._repo.fetch_projection_edges_for_node_ids(node_ids=node_ids)

    async def list_projection_edges_touching_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionEdge]:
        return await self._repo.fetch_projection_edges_touching_node_ids(node_ids=node_ids)

    async def list_projection_edges_for_edge_ids(
        self,
        *,
        edge_ids: list[int],
    ) -> list[ProjectionEdge]:
        return await self._repo.fetch_projection_edges_for_edge_ids(edge_ids=edge_ids)

    async def list_adjacent_edge_ids_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[int]:
        return await self._repo.fetch_adjacent_edge_ids_for_node_ids(node_ids=node_ids)

    async def list_unassigned_nodes_for_taxonomy_classification(
        self,
        *,
        limit: int | None,
    ) -> list[TaxonomyClassificationNodeInput]:
        if limit is not None and limit < 1:
            return []
        return await self._repo.fetch_unassigned_nodes_for_taxonomy_classification(
            limit=limit,
        )

    async def materialize_card_from_ingestion(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        try:
            node_id = await self._repo.create_node(
                title=title,
                content=content,
                embedding=embedding,
            )
            if self._taxonomy_projection_port is not None:
                await self._taxonomy_projection_port.assign_node_to_root_unclassified(
                    node_id=node_id,
                )
            candidates = await self._repo.search_similarity_candidates(
                query_embedding=embedding,
                excluded_node_ids=[node_id],
            )
            threshold_candidates = [
                candidate
                for candidate in candidates
                if candidate.similarity >= self._edge_similarity_min_strength
            ]
            for candidate in threshold_candidates[: self._edge_similarity_top_k]:
                edge_id = await self._repo.create_edge_with_adjacency(
                    source_node_id=node_id,
                    related_node_id=candidate.node_id,
                    strength=candidate.similarity,
                )
                if self._taxonomy_projection_port is not None:
                    leaf_ids_by_node_id = (
                        await self._taxonomy_projection_port.list_leaf_ids_for_node_ids(
                            node_ids=[node_id, candidate.node_id]
                        )
                    )
                    for leaf_id in sorted(set(leaf_ids_by_node_id.values())):
                        await self._taxonomy_projection_port.add_projected_edge_ids_for_leaf(
                            leaf_id=leaf_id,
                            edge_ids=[edge_id],
                        )

            await self._repo.commit()
            return node_id
        except Exception:
            await self._repo.rollback()
            raise
