"""
Abstract: Shared semantic-map metadata definitions used by read and rebuild
flows.
Out of scope: SQLAlchemy persistence and FastAPI route serialization.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from modules.semantic_map.types import Bounds4, Point2


class SemanticMapMetadataModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)


class CoordinateSystemDefinition(SemanticMapMetadataModel):
    kind: Literal["cartesian2d"]
    axis_direction: Literal["x-right-y-up"]
    bounds_format: Literal["min_x_min_y_max_x_max_y"]


class SemanticLevelDefinition(SemanticMapMetadataModel):
    level: int
    stable_id: str
    display_name: str
    min_zoom: int
    max_zoom: int
    region_role: str
    child_content_role: str


SEMANTIC_MAP_COORDINATE_SYSTEM = CoordinateSystemDefinition(
    kind="cartesian2d",
    axis_direction="x-right-y-up",
    bounds_format="min_x_min_y_max_x_max_y",
)

WORLD_BOUNDS: Bounds4 = (0.0, 0.0, 1_000.0, 1_000.0)
DEFAULT_VIEW_TARGET: Point2 = (500.0, 500.0)
DEFAULT_TILE_SIZE = 512

DEFAULT_PHASE1_SEMANTIC_LEVELS: tuple[SemanticLevelDefinition, ...] = (
    SemanticLevelDefinition(
        level=0,
        stable_id="domains",
        display_name="Domains",
        min_zoom=0,
        max_zoom=1,
        region_role="domain",
        child_content_role="theme",
    ),
    SemanticLevelDefinition(
        level=1,
        stable_id="themes",
        display_name="Themes",
        min_zoom=2,
        max_zoom=3,
        region_role="theme",
        child_content_role="topic",
    ),
    SemanticLevelDefinition(
        level=2,
        stable_id="topics",
        display_name="Topics",
        min_zoom=4,
        max_zoom=6,
        region_role="topic",
        child_content_role="point",
    ),
)
