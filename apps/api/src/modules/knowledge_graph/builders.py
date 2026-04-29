"""
Abstract: Module-local builders for assembling knowledge-graph domain services.
Out of scope: FastAPI dependency providers and worker actor wiring.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.repo import KnowledgeRepo
from modules.knowledge_graph.service import KnowledgeGraphService
from modules.taxonomy.repo import TaxonomyRepo


def build_knowledge_graph_service(
    *,
    session: AsyncSession,
    edge_title_mention_top_k: int,
    edge_semantic_top_k: int,
    edge_semantic_min_strength: float,
    edge_semantic_candidate_limit: int,
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        repo=KnowledgeRepo(session=session),
        edge_title_mention_top_k=edge_title_mention_top_k,
        edge_semantic_top_k=edge_semantic_top_k,
        edge_semantic_min_strength=edge_semantic_min_strength,
        edge_semantic_candidate_limit=edge_semantic_candidate_limit,
        taxonomy_projection_port=TaxonomyRepo(session=session),
    )
