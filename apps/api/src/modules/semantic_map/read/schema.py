"""
Abstract: Pydantic transport models for semantic-map HTTP responses.
Out of scope: Build orchestration and SQLAlchemy persistence behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from modules.semantic_map.core.dto import DefaultView
from modules.semantic_map.core.types import (
    Bounds4,
    LabelPayload,
    MultiPolygonGeometryPayload,
    PointPayload,
    PolygonGeometryPayload,
    RegionGeometryPayload,
    RegionPayload,
)
from modules.semantic_map.metadata import SemanticLevelDefinition


class SemanticMapResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CoordinateSystemResponse(SemanticMapResponseModel):
    kind: Literal["cartesian2d"]
    axis_direction: Literal["x-right-y-up"]
    bounds_format: Literal["min_x_min_y_max_x_max_y"]


class DefaultViewResponse(DefaultView):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SemanticLevelResponse(SemanticLevelDefinition):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class PolygonGeometryResponse(PolygonGeometryPayload):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class MultiPolygonGeometryResponse(MultiPolygonGeometryPayload):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


type RegionGeometryResponse = RegionGeometryPayload


class RegionResponse(RegionPayload):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class LabelResponse(LabelPayload):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class PointResponse(PointPayload):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SemanticMapManifestResponse(SemanticMapResponseModel):
    version: str
    schema_version: str
    built_at: datetime
    coordinate_system: CoordinateSystemResponse
    world_bounds: Bounds4
    tile_size: int
    max_zoom: int
    default_view: DefaultViewResponse
    default_semantic_level: int
    semantic_levels: list[SemanticLevelResponse]


class SemanticMapTileMetadataResponse(SemanticMapResponseModel):
    z: int
    x: int
    y: int
    tile_bounds: Bounds4
    bounds_format: Literal["min_x_min_y_max_x_max_y"]


class SemanticMapTileStatsResponse(SemanticMapResponseModel):
    region_count: int
    label_count: int


class SemanticMapTileResponse(SemanticMapResponseModel):
    schema_version: str
    version: str
    semantic_level: int
    tile: SemanticMapTileMetadataResponse
    stats: SemanticMapTileStatsResponse
    regions: list[RegionResponse]
    labels: list[LabelResponse]
    points: list[PointResponse]
