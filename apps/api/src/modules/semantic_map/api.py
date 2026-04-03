"""
Abstract: FastAPI route contract for semantic-map manifest and region-tile
reads.
Out of scope: Dependency construction and snapshot rebuild orchestration.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends

from modules.semantic_map.schema import SemanticMapManifestResponse, SemanticMapTileResponse
from modules.semantic_map.service import SemanticMapService

SemanticMapServiceProvider = Callable[..., SemanticMapService]


def build_router(*, get_semantic_map_service: SemanticMapServiceProvider) -> APIRouter:
    router = APIRouter(tags=["semantic-map"])

    @router.get(
        "/semantic-map/manifest/current",
        response_model=SemanticMapManifestResponse,
    )
    async def get_current_manifest(
        semantic_map_service: SemanticMapService = Depends(get_semantic_map_service),
    ) -> SemanticMapManifestResponse:
        return await semantic_map_service.get_current_manifest()

    @router.get(
        "/semantic-map/versions/{version}/tiles/regions/{semantic_level}/{z}/{x}/{y}",
        response_model=SemanticMapTileResponse,
    )
    async def get_region_tile(
        version: str,
        semantic_level: int,
        z: int,
        x: int,
        y: int,
        semantic_map_service: SemanticMapService = Depends(get_semantic_map_service),
    ) -> SemanticMapTileResponse:
        return await semantic_map_service.get_region_tile(
            version=version,
            semantic_level=semantic_level,
            tile_z=z,
            tile_x=x,
            tile_y=y,
        )

    return router
