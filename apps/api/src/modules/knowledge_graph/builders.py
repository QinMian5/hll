"""
Abstract: Module-local builders for assembling knowledge-graph domain services.
Out of scope: FastAPI dependency providers and worker actor wiring.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.repo import KnowledgeRepo
from modules.knowledge_graph.service import KnowledgeGraphService


def build_knowledge_graph_service(
    *,
    session: AsyncSession,
    edge_similarity_top_k: int,
    edge_similarity_min_strength: float,
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        repo=KnowledgeRepo(session=session),
        edge_similarity_top_k=edge_similarity_top_k,
        edge_similarity_min_strength=edge_similarity_min_strength,
    )
