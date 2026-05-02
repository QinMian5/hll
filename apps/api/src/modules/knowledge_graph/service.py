"""
Abstract: Knowledge-graph domain service for retrieval orchestration and ingestion
materialization rules.
Out of scope: HTTP endpoint concerns, queue transport, and dependency injection.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

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
from modules.taxonomy.dto import TaxonomyScopeIdentity

RRF_K = 60


def _rrf(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return 1.0 / (RRF_K + rank)


def _title_boost_tuple(candidate: LexicalSearchCandidate | None) -> tuple[int, int, int]:
    if candidate is None:
        return (0, 0, 0)
    return (
        int(candidate.exact_title_match),
        int(candidate.title_phrase_match),
        int(candidate.title_all_tokens_match),
    )


class CardVersionNotFoundError(ValueError):
    pass


class CardSuggestedEditNoChangeError(ValueError):
    pass


class KnowledgeGraphRepoProtocol(Protocol):
    async def search_vector_candidates(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[VectorSearchCandidate]: ...

    async def search_lexical_candidates(
        self,
        *,
        query_text: str,
        limit: int,
    ) -> list[LexicalSearchCandidate]: ...

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

    async def fetch_projection_card_titles_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[ProjectionCardTitle]: ...

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

    async def fetch_card_version(
        self,
        *,
        node_id: int,
        version: int,
    ) -> CardVersionSnapshot | None: ...

    async def create_card_suggested_edit(
        self,
        *,
        node_id: int,
        base_version: int,
        suggested_title: str,
        suggested_content: str,
        suggested_by_user_id: str,
    ) -> CardSuggestedEditRecord: ...

    async def search_similarity_candidates(
        self,
        *,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
        limit: int,
    ) -> list[SimilarNodeCandidate]: ...

    async def search_title_mention_candidates(
        self,
        *,
        content: str,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
        limit: int,
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
    async def assign_node_to_root(self, *, node_id: int) -> int: ...

    async def list_scope_identities_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, TaxonomyScopeIdentity]: ...

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None: ...


class KnowledgeGraphService:
    def __init__(
        self,
        *,
        repo: KnowledgeGraphRepoProtocol,
        edge_title_mention_top_k: int,
        edge_semantic_top_k: int,
        edge_semantic_min_strength: float,
        edge_semantic_candidate_limit: int,
        taxonomy_projection_port: KnowledgeGraphTaxonomyProjectionPort | None = None,
    ) -> None:
        self._repo = repo
        self._edge_title_mention_top_k = edge_title_mention_top_k
        self._edge_semantic_top_k = edge_semantic_top_k
        self._edge_semantic_min_strength = edge_semantic_min_strength
        self._edge_semantic_candidate_limit = edge_semantic_candidate_limit
        self._taxonomy_projection_port = taxonomy_projection_port

    async def search_searchable_cards(
        self,
        *,
        query_text: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]:
        if limit <= 0:
            return []

        vector_candidates = await self._repo.search_vector_candidates(
            query_embedding=query_embedding,
            limit=limit,
        )
        lexical_candidates = await self._repo.search_lexical_candidates(
            query_text=query_text,
            limit=limit,
        )

        matches_by_node_id: dict[int, KnowledgeCardMatch] = {}
        vector_ranks_by_node_id: dict[int, int] = {}
        lexical_by_node_id: dict[int, LexicalSearchCandidate] = {}

        for candidate in vector_candidates:
            matches_by_node_id.setdefault(
                candidate.node_id,
                KnowledgeCardMatch(
                    node_id=candidate.node_id,
                    current_version=candidate.current_version,
                    title=candidate.title,
                    content=candidate.content,
                ),
            )
            vector_ranks_by_node_id[candidate.node_id] = candidate.vector_rank

        for candidate in lexical_candidates:
            matches_by_node_id[candidate.node_id] = KnowledgeCardMatch(
                node_id=candidate.node_id,
                current_version=candidate.current_version,
                title=candidate.title,
                content=candidate.content,
            )
            lexical_by_node_id[candidate.node_id] = candidate

        def sort_key(
            match: KnowledgeCardMatch,
        ) -> tuple[int, int, int, float, float, int, int, int]:
            lexical_candidate = lexical_by_node_id.get(match.node_id)
            vector_rank = vector_ranks_by_node_id.get(match.node_id)
            lexical_rank = (
                lexical_candidate.lexical_rank if lexical_candidate is not None else limit + 1
            )
            vector_sort_rank = vector_rank if vector_rank is not None else limit + 1
            fused_score = _rrf(vector_rank) + _rrf(lexical_rank if lexical_candidate else None)
            lexical_score = (
                lexical_candidate.lexical_score if lexical_candidate is not None else 0.0
            )
            exact_boost, phrase_boost, all_tokens_boost = _title_boost_tuple(lexical_candidate)
            return (
                -exact_boost,
                -phrase_boost,
                -all_tokens_boost,
                -fused_score,
                -lexical_score,
                lexical_rank,
                vector_sort_rank,
                match.node_id,
            )

        return sorted(matches_by_node_id.values(), key=sort_key)[:limit]

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

    async def list_projection_card_titles_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionCardTitle]:
        return await self._repo.fetch_projection_card_titles_for_node_ids(node_ids=node_ids)

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

    async def submit_card_suggested_edit(
        self,
        *,
        node_id: int,
        base_version: int,
        suggested_title: str,
        suggested_content: str,
        suggested_by_user_id: str,
    ) -> CardSuggestedEditRecord:
        try:
            base = await self._repo.fetch_card_version(
                node_id=node_id,
                version=base_version,
            )
            if base is None:
                raise CardVersionNotFoundError("Card base version does not exist.")
            if suggested_title == base.title and suggested_content == base.content:
                raise CardSuggestedEditNoChangeError("Suggested edit must change title or content.")
            record = await self._repo.create_card_suggested_edit(
                node_id=node_id,
                base_version=base_version,
                suggested_title=suggested_title,
                suggested_content=suggested_content,
                suggested_by_user_id=suggested_by_user_id,
            )
            await self._repo.commit()
            return record
        except Exception:
            await self._repo.rollback()
            raise

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
                await self._taxonomy_projection_port.assign_node_to_root(
                    node_id=node_id,
                )

            selected_node_ids: list[int] = []
            selected_node_id_set: set[int] = set()

            if self._edge_title_mention_top_k > 0:
                title_mention_candidates = await self._repo.search_title_mention_candidates(
                    content=content,
                    query_embedding=embedding,
                    excluded_node_ids=[node_id],
                    limit=self._edge_title_mention_top_k,
                )
                title_mention_edge_count = 0
                for candidate in title_mention_candidates:
                    if candidate.node_id in selected_node_id_set:
                        continue
                    await self._create_edge_with_projection(
                        source_node_id=node_id,
                        related_node_id=candidate.node_id,
                        strength=candidate.similarity,
                    )
                    selected_node_ids.append(candidate.node_id)
                    selected_node_id_set.add(candidate.node_id)
                    title_mention_edge_count += 1
                    if title_mention_edge_count >= self._edge_title_mention_top_k:
                        break

            if self._edge_semantic_top_k > 0:
                candidates = await self._repo.search_similarity_candidates(
                    query_embedding=embedding,
                    excluded_node_ids=[node_id, *selected_node_ids],
                    limit=self._edge_semantic_candidate_limit,
                )
                semantic_edge_count = 0
                for candidate in candidates:
                    if candidate.node_id in selected_node_id_set:
                        continue
                    if candidate.similarity < self._edge_semantic_min_strength:
                        continue
                    await self._create_edge_with_projection(
                        source_node_id=node_id,
                        related_node_id=candidate.node_id,
                        strength=candidate.similarity,
                    )
                    selected_node_ids.append(candidate.node_id)
                    selected_node_id_set.add(candidate.node_id)
                    semantic_edge_count += 1
                    if semantic_edge_count >= self._edge_semantic_top_k:
                        break

            await self._repo.commit()
            return node_id
        except Exception:
            await self._repo.rollback()
            raise

    async def _create_edge_with_projection(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> None:
        edge_id = await self._repo.create_edge_with_adjacency(
            source_node_id=source_node_id,
            related_node_id=related_node_id,
            strength=strength,
        )
        if self._taxonomy_projection_port is not None:
            scope_identities_by_node_id = (
                await self._taxonomy_projection_port.list_scope_identities_for_node_ids(
                    node_ids=[source_node_id, related_node_id]
                )
            )
            scope_identities = sorted(
                set(scope_identities_by_node_id.values()),
                key=lambda item: (item.scope_kind, item.taxonomy_node_id),
            )
            for scope_identity in scope_identities:
                await self._taxonomy_projection_port.add_projected_edge_ids_for_scope(
                    scope_identity=scope_identity,
                    edge_ids=[edge_id],
                )
