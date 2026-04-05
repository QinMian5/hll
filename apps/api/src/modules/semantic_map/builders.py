"""
Abstract: Module-local builders for assembling semantic-map services.
Out of scope: FastAPI dependency providers and shell-script runtime composition.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.ports import KnowledgeGraphProjectionPort
from modules.semantic_map.persistence.repo import SemanticMapRepo
from modules.semantic_map.read.service import SemanticMapService
from modules.semantic_map.snapshot_build.service import SemanticMapBuildService
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.service import TaxonomyService


def build_semantic_map_service(*, session: AsyncSession) -> SemanticMapService:
    return SemanticMapService(
        repo=SemanticMapRepo(session=session),
    )


def build_semantic_map_build_service(
    *,
    session: AsyncSession,
    projection_port: KnowledgeGraphProjectionPort,
) -> SemanticMapBuildService:
    return SemanticMapBuildService(
        projection_port=projection_port,
        taxonomy_port=TaxonomyService(repo=TaxonomyRepo(session=session)),
        snapshot_repo=SemanticMapRepo(session=session),
    )
