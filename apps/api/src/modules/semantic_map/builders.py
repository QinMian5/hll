"""
Abstract: Module-local builders for assembling semantic-map services.
Out of scope: FastAPI dependency providers and shell-script runtime composition.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.ports import KnowledgeGraphProjectionPort
from modules.semantic_map.rebuild import SemanticMapRebuildService
from modules.semantic_map.repo import SemanticMapRepo


def build_semantic_map_rebuild_service(
    *,
    session: AsyncSession,
    projection_port: KnowledgeGraphProjectionPort,
) -> SemanticMapRebuildService:
    return SemanticMapRebuildService(
        projection_port=projection_port,
        snapshot_repo=SemanticMapRepo(session=session),
    )
