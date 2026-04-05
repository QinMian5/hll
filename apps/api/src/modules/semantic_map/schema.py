"""
Abstract: Pydantic transport models for semantic-map HTTP responses.
Out of scope: Rebuild orchestration and SQLAlchemy persistence behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from modules.semantic_map.types import Bounds4, Point2


class SemanticMapResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CoordinateSystemResponse(SemanticMapResponseModel):
    kind: Literal["cartesian2d"]
    axis_direction: Literal["x-right-y-up"]
    bounds_format: Literal["min_x_min_y_max_x_max_y"]


class DefaultViewResponse(SemanticMapResponseModel):
    target: Point2
    zoom: float


class SemanticLevelResponse(SemanticMapResponseModel):
    level: int
    stable_id: str
    display_name: str
    min_zoom: int
    max_zoom: int
    region_role: str
    child_content_role: str


class PolygonGeometryResponse(SemanticMapResponseModel):
    type: Literal["polygon"]
    coordinates: list[list[float]]


class MultiPolygonGeometryResponse(SemanticMapResponseModel):
    type: Literal["multi_polygon"]
    coordinates: list[list[list[float]]]


type RegionGeometryResponse = Annotated[
    PolygonGeometryResponse | MultiPolygonGeometryResponse,
    Field(discriminator="type"),
]


class RegionResponse(SemanticMapResponseModel):
    id: str
    parent_id: str | None
    region_name: str
    centroid: list[float]
    bbox: list[float]
    geometry: RegionGeometryResponse
    display_rank: int
    children_available: bool


class LabelResponse(SemanticMapResponseModel):
    id: str
    region_id: str
    text: str
    position: list[float]
    label_rank: int
    font_size: int


class PointResponse(SemanticMapResponseModel):
    id: str
    node_id: int
    leaf_region_id: str
    title: str
    position: list[float]


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
