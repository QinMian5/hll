"""
Abstract: Knowledge-graph domain service for retrieval orchestration and ingestion
materialization rules.
Out of scope: HTTP endpoint concerns, queue transport, and dependency injection.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

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
    SearchableCardResult,
    SimilarNodeCandidate,
    TaxonomyClassificationNodeInput,
    VectorSearchCandidate,
)
from modules.taxonomy.dto import TaxonomyScopeIdentity
from shared.integrations import EmbeddingClientPort

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


def _payload_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise CardProposalValidationError(f"Proposal payload missing {key}.")
    return value


def _payload_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 1:
        raise CardProposalValidationError(f"Proposal payload missing {key}.")
    return value


class CardVersionNotFoundError(ValueError):
    pass


class CardSuggestedEditNoChangeError(ValueError):
    pass


class CardProposalNotFoundError(ValueError):
    pass


class CardProposalInvalidStateError(ValueError):
    pass


class CardProposalPermissionError(PermissionError):
    pass


class CardProposalValidationError(ValueError):
    pass


def _normalize_reason(reason: str | None) -> str:
    if reason is None or reason.strip() == "":
        raise CardProposalValidationError("Card proposals require a reason.")
    return reason.strip()


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
        reason: str,
    ) -> CardSuggestedEditRecord: ...

    async def create_card_proposal(
        self,
        *,
        proposal_type: str,
        submitted_by_user_id: str,
        reason: str,
        payload: dict[str, object],
    ) -> CardProposalRecord: ...

    async def fetch_card_proposal(self, *, proposal_id: int) -> CardProposalRecord | None: ...

    async def list_card_proposals_for_user(self, *, user_id: str) -> list[CardProposalRecord]: ...

    async def list_pending_card_proposals(self) -> list[CardProposalRecord]: ...

    async def has_active_workspace_review_role(self, *, user_id: str) -> bool: ...

    async def create_next_card_version(
        self,
        *,
        node_id: int,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int: ...

    async def archive_node(self, *, node_id: int) -> None: ...

    async def mark_card_proposal_accepted(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
        affected_node_ids: list[int],
        created_versions: list[dict[str, int]],
        archive_outcome: dict[str, object] | None,
    ) -> CardProposalRecord: ...

    async def mark_card_proposal_rejected(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
    ) -> CardProposalRecord: ...

    async def mark_card_proposal_withdrawn(
        self,
        *,
        proposal_id: int,
    ) -> CardProposalRecord: ...

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
    ) -> None: ...

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
        embedding_client: EmbeddingClientPort | None = None,
    ) -> None:
        self._repo = repo
        self._edge_title_mention_top_k = edge_title_mention_top_k
        self._edge_semantic_top_k = edge_semantic_top_k
        self._edge_semantic_min_strength = edge_semantic_min_strength
        self._edge_semantic_candidate_limit = edge_semantic_candidate_limit
        self._taxonomy_projection_port = taxonomy_projection_port
        self._embedding_client = embedding_client

    async def search_searchable_cards(
        self,
        *,
        query_text: str,
        query_embedding: list[float],
        limit: int,
        vector_candidate_limit: int,
    ) -> SearchableCardResult:
        if limit <= 0:
            return SearchableCardResult(matches=[], vector_candidate_count=0)
        if vector_candidate_limit < limit:
            raise ValueError("vector_candidate_limit must be greater than or equal to limit.")

        vector_candidates = await self._repo.search_vector_candidates(
            query_embedding=query_embedding,
            limit=vector_candidate_limit,
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

        return SearchableCardResult(
            matches=sorted(matches_by_node_id.values(), key=sort_key)[:limit],
            vector_candidate_count=len(vector_candidates),
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
        reason: str,
    ) -> CardSuggestedEditRecord:
        try:
            normalized_reason = _normalize_reason(reason)
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
                reason=normalized_reason,
            )
            await self._repo.commit()
            return record
        except Exception:
            await self._repo.rollback()
            raise

    async def submit_card_proposal(
        self,
        *,
        proposal_type: CardProposalType,
        submitted_by_user_id: str,
        proposed_title: str | None = None,
        proposed_content: str | None = None,
        target_node_id: int | None = None,
        base_version: int | None = None,
        suggested_title: str | None = None,
        suggested_content: str | None = None,
        reason: str,
    ) -> CardProposalRecord:
        try:
            normalized_reason = _normalize_reason(reason)
            payload = await self._build_proposal_payload(
                proposal_type=proposal_type,
                proposed_title=proposed_title,
                proposed_content=proposed_content,
                target_node_id=target_node_id,
                base_version=base_version,
                suggested_title=suggested_title,
                suggested_content=suggested_content,
                reason=normalized_reason,
            )
            record = await self._repo.create_card_proposal(
                proposal_type=proposal_type,
                submitted_by_user_id=submitted_by_user_id,
                reason=normalized_reason,
                payload=payload,
            )
            await self._repo.commit()
            return record
        except Exception:
            await self._repo.rollback()
            raise

    async def list_card_proposals_for_user(self, *, user_id: str) -> list[CardProposalRecord]:
        return await self._repo.list_card_proposals_for_user(user_id=user_id)

    async def list_pending_card_proposals_for_review(
        self,
        *,
        reviewer_user_id: str,
    ) -> list[CardProposalRecord]:
        if not await self._repo.has_active_workspace_review_role(user_id=reviewer_user_id):
            raise CardProposalPermissionError("Reviewer role is required.")
        return await self._repo.list_pending_card_proposals()

    async def reject_card_proposal(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
    ) -> CardProposalRecord:
        try:
            proposal = await self._fetch_pending_proposal(proposal_id=proposal_id)
            if not await self._repo.has_active_workspace_review_role(user_id=reviewer_user_id):
                raise CardProposalPermissionError("Reviewer role is required.")
            record = await self._repo.mark_card_proposal_rejected(
                proposal_id=proposal.id,
                reviewer_user_id=reviewer_user_id,
                review_note=review_note,
            )
            await self._repo.commit()
            return record
        except Exception:
            await self._repo.rollback()
            raise

    async def withdraw_card_proposal(
        self,
        *,
        proposal_id: int,
        user_id: str,
    ) -> CardProposalRecord:
        try:
            proposal = await self._fetch_pending_proposal(proposal_id=proposal_id)
            if proposal.submitted_by_user_id != user_id:
                raise CardProposalPermissionError("Only the submitter can withdraw this proposal.")
            record = await self._repo.mark_card_proposal_withdrawn(proposal_id=proposal.id)
            await self._repo.commit()
            return record
        except Exception:
            await self._repo.rollback()
            raise

    async def accept_card_proposal(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
    ) -> CardProposalRecord:
        try:
            if not await self._repo.has_active_workspace_review_role(user_id=reviewer_user_id):
                raise CardProposalPermissionError("Reviewer role is required.")
            proposal = await self._fetch_pending_proposal(proposal_id=proposal_id)
            affected_node_ids, created_versions, archive_outcome = await self._apply_proposal(
                proposal=proposal
            )
            record = await self._repo.mark_card_proposal_accepted(
                proposal_id=proposal.id,
                reviewer_user_id=reviewer_user_id,
                review_note=review_note,
                affected_node_ids=affected_node_ids,
                created_versions=created_versions,
                archive_outcome=archive_outcome,
            )
            await self._repo.create_proposal_apply_audit(
                proposal_id=proposal.id,
                reviewer_user_id=reviewer_user_id,
                proposal_type=proposal.proposal_type,
                affected_node_ids=affected_node_ids,
                created_versions=created_versions,
                archive_outcome=archive_outcome,
                review_note=review_note,
            )
            await self._repo.commit()
            return record
        except Exception:
            await self._repo.rollback()
            raise

    async def _build_proposal_payload(
        self,
        *,
        proposal_type: CardProposalType,
        proposed_title: str | None,
        proposed_content: str | None,
        target_node_id: int | None,
        base_version: int | None,
        suggested_title: str | None,
        suggested_content: str | None,
        reason: str,
    ) -> dict[str, object]:
        _normalize_reason(reason)
        if proposal_type == "create":
            if proposed_title is None or proposed_content is None:
                raise CardProposalValidationError("Create proposals require title and content.")
            return {
                "proposed_title": proposed_title,
                "proposed_content": proposed_content,
            }

        if target_node_id is None or base_version is None:
            raise CardProposalValidationError(
                "Card proposal requires target node and base version."
            )
        base = await self._repo.fetch_card_version(node_id=target_node_id, version=base_version)
        if base is None:
            raise CardVersionNotFoundError("Card base version does not exist.")

        if proposal_type == "edit":
            if suggested_title is None or suggested_content is None:
                raise CardProposalValidationError("Edit proposals require title and content.")
            if suggested_title == base.title and suggested_content == base.content:
                raise CardSuggestedEditNoChangeError("Suggested edit must change title or content.")
            return {
                "target_node_id": target_node_id,
                "base_version": base_version,
                "suggested_title": suggested_title,
                "suggested_content": suggested_content,
            }

        if proposal_type == "delete":
            return {
                "target_node_id": target_node_id,
                "base_version": base_version,
                "target_title": base.title,
                "target_content": base.content,
            }

        raise CardProposalValidationError("Unsupported proposal type.")

    async def _fetch_pending_proposal(self, *, proposal_id: int) -> CardProposalRecord:
        proposal = await self._repo.fetch_card_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise CardProposalNotFoundError("Proposal does not exist.")
        if proposal.status != "pending_review":
            raise CardProposalInvalidStateError("Proposal is not pending review.")
        return proposal

    async def _apply_proposal(
        self,
        *,
        proposal: CardProposalRecord,
    ) -> tuple[list[int], list[dict[str, int]], dict[str, object] | None]:
        proposal_type = proposal.proposal_type
        if proposal_type == "create":
            return await self._apply_create_proposal(proposal=proposal)
        if proposal_type == "edit":
            return await self._apply_edit_proposal(proposal=proposal)
        if proposal_type == "delete":
            return await self._apply_delete_proposal(proposal=proposal)
        raise CardProposalValidationError("Unsupported proposal type.")

    async def _apply_create_proposal(
        self,
        *,
        proposal: CardProposalRecord,
    ) -> tuple[list[int], list[dict[str, int]], None]:
        title = _payload_text(proposal.payload, "proposed_title")
        content = _payload_text(proposal.payload, "proposed_content")
        embedding = await self._embed_card(title=title, content=content)
        node_id = await self._repo.create_node(title=title, content=content, embedding=embedding)
        if self._taxonomy_projection_port is not None:
            await self._taxonomy_projection_port.assign_node_to_root(node_id=node_id)
        return [node_id], [{"node_id": node_id, "version": 1}], None

    async def _apply_edit_proposal(
        self,
        *,
        proposal: CardProposalRecord,
    ) -> tuple[list[int], list[dict[str, int]], None]:
        node_id = _payload_int(proposal.payload, "target_node_id")
        title = _payload_text(proposal.payload, "suggested_title")
        content = _payload_text(proposal.payload, "suggested_content")
        embedding = await self._embed_card(title=title, content=content)
        version = await self._repo.create_next_card_version(
            node_id=node_id,
            title=title,
            content=content,
            embedding=embedding,
        )
        return [node_id], [{"node_id": node_id, "version": version}], None

    async def _apply_delete_proposal(
        self,
        *,
        proposal: CardProposalRecord,
    ) -> tuple[list[int], list[dict[str, int]], dict[str, object]]:
        node_id = _payload_int(proposal.payload, "target_node_id")
        await self._repo.archive_node(node_id=node_id)
        return [node_id], [], {"archived_node_id": node_id}

    async def _embed_card(self, *, title: str, content: str) -> list[float]:
        if self._embedding_client is None:
            raise CardProposalValidationError("Embedding client is required to apply proposals.")
        return await self._embedding_client.embed_text(f"{title}\n\n{content}")

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
