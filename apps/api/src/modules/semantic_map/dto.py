"""
Abstract: Internal semantic-map value objects for repository inputs and outputs.
Out of scope: SQLAlchemy table mapping and HTTP transport serialization.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from modules.semantic_map.metadata import SemanticLevelDefinition
from modules.semantic_map.types import Bounds4, LabelPayload, Point2, PointPayload, RegionPayload


class SemanticMapValueModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)


class DefaultView(SemanticMapValueModel):
    target: Point2
    zoom: float


class SemanticMapManifest(SemanticMapValueModel):
    version: str
    schema_version: str
    built_at: datetime
    world_bounds: Bounds4
    tile_size: int
    max_zoom: int
    default_view: DefaultView
    default_semantic_level: int
    semantic_levels: list[SemanticLevelDefinition]


class SemanticMapRegionTile(SemanticMapValueModel):
    semantic_level: int
    tile_z: int
    tile_x: int
    tile_y: int
    tile_bounds: Bounds4
    region_count: int
    label_count: int
    regions: list[RegionPayload]
    labels: list[LabelPayload]
    points: list[PointPayload]
