"""
Abstract: Read-side semantic-map service for manifest and tile HTTP contract
responses.
Out of scope: Build orchestration and direct SQLAlchemy query execution.
"""

from __future__ import annotations

from collections.abc import Sequence

from core.errors import ApplicationError, DomainError, ErrorCode
from modules.semantic_map.core.dto import SemanticMapManifest, SemanticMapRegionTile
from modules.semantic_map.core.geometry import tile_bounds_for_coordinate
from modules.semantic_map.metadata import (
    SEMANTIC_MAP_COORDINATE_SYSTEM,
    CoordinateSystemDefinition,
    SemanticLevelDefinition,
)
from modules.semantic_map.ports import SemanticMapSnapshotReadPort
from modules.semantic_map.read.schema import (
    CoordinateSystemResponse,
    DefaultViewResponse,
    LabelResponse,
    PointResponse,
    RegionResponse,
    SemanticLevelResponse,
    SemanticMapManifestResponse,
    SemanticMapTileMetadataResponse,
    SemanticMapTileResponse,
    SemanticMapTileStatsResponse,
)


def _coordinate_system_response(
    coordinate_system: CoordinateSystemDefinition,
) -> CoordinateSystemResponse:
    return CoordinateSystemResponse(
        kind=coordinate_system.kind,
        axis_direction=coordinate_system.axis_direction,
        bounds_format=coordinate_system.bounds_format,
    )


def _semantic_level_response(level: SemanticLevelDefinition) -> SemanticLevelResponse:
    return SemanticLevelResponse(
        level=level.level,
        stable_id=level.stable_id,
        display_name=level.display_name,
        min_zoom=level.min_zoom,
        max_zoom=level.max_zoom,
        region_role=level.region_role,
        child_content_role=level.child_content_role,
    )


def _manifest_response(
    manifest: SemanticMapManifest,
    *,
    coordinate_system: CoordinateSystemDefinition,
) -> SemanticMapManifestResponse:
    return SemanticMapManifestResponse(
        version=manifest.version,
        schema_version=manifest.schema_version,
        built_at=manifest.built_at,
        coordinate_system=_coordinate_system_response(coordinate_system),
        world_bounds=manifest.world_bounds,
        tile_size=manifest.tile_size,
        max_zoom=manifest.max_zoom,
        default_view=DefaultViewResponse(
            target=manifest.default_view.target,
            zoom=manifest.default_view.zoom,
        ),
        default_semantic_level=manifest.default_semantic_level,
        semantic_levels=[_semantic_level_response(level) for level in manifest.semantic_levels],
    )


def _tile_response(
    *,
    manifest: SemanticMapManifest,
    semantic_level: int,
    tile_z: int,
    tile_x: int,
    tile_y: int,
    tile: SemanticMapRegionTile | None,
    coordinate_system: CoordinateSystemDefinition,
) -> SemanticMapTileResponse:
    tile_bounds = (
        tile.tile_bounds
        if tile is not None
        else tile_bounds_for_coordinate(
            world_bounds=manifest.world_bounds,
            zoom=tile_z,
            tile_x=tile_x,
            tile_y=tile_y,
        )
    )
    regions = [] if tile is None else tile.regions
    labels = [] if tile is None else tile.labels
    points = [] if tile is None else tile.points

    return SemanticMapTileResponse(
        schema_version=manifest.schema_version,
        version=manifest.version,
        semantic_level=semantic_level,
        tile=SemanticMapTileMetadataResponse(
            z=tile_z,
            x=tile_x,
            y=tile_y,
            tile_bounds=tile_bounds,
            bounds_format=coordinate_system.bounds_format,
        ),
        stats=SemanticMapTileStatsResponse(
            region_count=0 if tile is None else tile.region_count,
            label_count=0 if tile is None else tile.label_count,
        ),
        regions=[
            RegionResponse(
                id=region.id,
                parent_id=region.parent_id,
                region_name=region.region_name,
                centroid=region.centroid,
                bbox=region.bbox,
                geometry=region.geometry,
                display_rank=region.display_rank,
                children_available=region.children_available,
            )
            for region in regions
        ],
        labels=[
            LabelResponse(
                id=label.id,
                region_id=label.region_id,
                text=label.text,
                position=label.position,
                label_rank=label.label_rank,
                font_size=label.font_size,
            )
            for label in labels
        ],
        points=[
            PointResponse(
                id=point.id,
                node_id=point.node_id,
                leaf_region_id=point.leaf_region_id,
                title=point.title,
                position=point.position,
            )
            for point in points
        ],
    )


class SemanticMapService:
    def __init__(
        self,
        *,
        repo: SemanticMapSnapshotReadPort,
        coordinate_system: CoordinateSystemDefinition = SEMANTIC_MAP_COORDINATE_SYSTEM,
    ) -> None:
        self._repo = repo
        self._coordinate_system = coordinate_system

    async def get_current_manifest(self) -> SemanticMapManifestResponse:
        manifest = await self._repo.get_current_manifest()
        if manifest is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND,
                message="Semantic-map snapshot is unavailable.",
                hint="Run a semantic-map build and retry.",
            )

        return _manifest_response(
            manifest,
            coordinate_system=self._coordinate_system,
        )

    async def get_region_tile(
        self,
        *,
        version: str,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
    ) -> SemanticMapTileResponse:
        manifest = await self._repo.get_manifest_by_version(version=version)
        if manifest is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND,
                message="Semantic-map snapshot version was not found.",
                hint="Refresh manifest/current and retry with an available version.",
            )

        self._validate_tile_request(
            semantic_level=semantic_level,
            tile_z=tile_z,
            tile_x=tile_x,
            tile_y=tile_y,
            semantic_levels=manifest.semantic_levels,
        )

        tile = await self._repo.get_region_tile(
            version=version,
            semantic_level=semantic_level,
            tile_z=tile_z,
            tile_x=tile_x,
            tile_y=tile_y,
        )
        return _tile_response(
            manifest=manifest,
            semantic_level=semantic_level,
            tile_z=tile_z,
            tile_x=tile_x,
            tile_y=tile_y,
            tile=tile,
            coordinate_system=self._coordinate_system,
        )

    def _validate_tile_request(
        self,
        *,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
        semantic_levels: Sequence[SemanticLevelDefinition],
    ) -> None:
        semantic_levels_by_level = {level.level: level for level in semantic_levels}
        if semantic_level not in semantic_levels_by_level:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_SEMANTIC_MAP_INPUT_INVALID,
                message="Semantic-map tile request is invalid.",
                hint="Use a supported semantic level and non-negative tile coordinates.",
            )

        if tile_z < 0 or tile_x < 0 or tile_y < 0:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_SEMANTIC_MAP_INPUT_INVALID,
                message="Semantic-map tile request is invalid.",
                hint="Use a supported semantic level and non-negative tile coordinates.",
            )
