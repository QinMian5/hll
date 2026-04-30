"""
Abstract: Module-local builders for assembling knowledge-graph domain services.
Out of scope: FastAPI dependency providers and worker actor wiring.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.repo import KnowledgeRepo
from modules.knowledge_graph.service import KnowledgeGraphService
from modules.taxonomy.projection_port import (
    CacheInvalidatingTaxonomyProjectionPort,
    TaxonomyLeafLayoutInvalidationPort,
)
from modules.taxonomy.repo import TaxonomyRepo


def build_knowledge_graph_service(
    *,
    session: AsyncSession,
    edge_title_mention_top_k: int,
    edge_semantic_top_k: int,
    edge_semantic_min_strength: float,
    edge_semantic_candidate_limit: int,
    taxonomy_view_cache: TaxonomyLeafLayoutInvalidationPort | None = None,
) -> KnowledgeGraphService:
    taxonomy_repo = TaxonomyRepo(session=session)
    taxonomy_projection_port = (
        CacheInvalidatingTaxonomyProjectionPort(
            repo=taxonomy_repo,
            view_cache=taxonomy_view_cache,
        )
        if taxonomy_view_cache is not None
        else taxonomy_repo
    )
    return KnowledgeGraphService(
        repo=KnowledgeRepo(session=session),
        edge_title_mention_top_k=edge_title_mention_top_k,
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
        edge_semantic_candidate_limit=edge_semantic_candidate_limit,
        taxonomy_projection_port=taxonomy_projection_port,
    )
