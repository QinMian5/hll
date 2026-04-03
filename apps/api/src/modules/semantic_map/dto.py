"""
Abstract: Internal semantic-map value objects for repository inputs and outputs.
Out of scope: SQLAlchemy table mapping and HTTP transport serialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from modules.semantic_map.types import Bounds4, JsonObject, Point2


@dataclass(frozen=True, slots=True)
class DefaultView:
    target: Point2
    zoom: float


@dataclass(frozen=True, slots=True)
class SemanticMapManifest:
    version: str
    schema_version: str
    built_at: datetime
    world_bounds: Bounds4
    tile_size: int
    max_zoom: int
    default_view: DefaultView
    default_semantic_level: int


@dataclass(frozen=True, slots=True)
class SemanticMapRegionTile:
    semantic_level: int
    tile_z: int
    tile_x: int
    tile_y: int
    tile_bounds: Bounds4
    region_count: int
    label_count: int
    regions: list[JsonObject]
    labels: list[JsonObject]
