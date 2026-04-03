"""
Abstract: FastAPI route contract for semantic-map manifest and region-tile
reads.
Out of scope: Dependency construction and snapshot rebuild orchestration.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends

from core.errors import ErrorEnvelope
from modules.semantic_map.schema import SemanticMapManifestResponse, SemanticMapTileResponse
from modules.semantic_map.service import SemanticMapService

SemanticMapServiceProvider = Callable[..., SemanticMapService]

_NOT_FOUND_RESPONSE = {
    "description": "Requested semantic-map snapshot was not found.",
    "model": ErrorEnvelope,
}
_SEMANTIC_MAP_INPUT_INVALID_RESPONSE = {
    "description": "Semantic-map tile parameters are invalid.",
    "model": ErrorEnvelope,
}


def build_router(*, get_semantic_map_service: SemanticMapServiceProvider) -> APIRouter:
    router = APIRouter(tags=["semantic-map"])

    @router.get(
        "/semantic-map/manifest/current",
        response_model=SemanticMapManifestResponse,
        responses={404: _NOT_FOUND_RESPONSE},
    )
    async def get_current_manifest(
        semantic_map_service: SemanticMapService = Depends(get_semantic_map_service),
    ) -> SemanticMapManifestResponse:
        return await semantic_map_service.get_current_manifest()

    @router.get(
        "/semantic-map/versions/{version}/tiles/regions/{semantic_level}/{z}/{x}/{y}",
        response_model=SemanticMapTileResponse,
        responses={
            400: _SEMANTIC_MAP_INPUT_INVALID_RESPONSE,
            404: _NOT_FOUND_RESPONSE,
        },
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
