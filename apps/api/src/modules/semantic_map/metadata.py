"""
Abstract: Shared semantic-map metadata definitions used by read and build
flows.
Out of scope: SQLAlchemy persistence and FastAPI route serialization.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from modules.semantic_map.core.types import Bounds4, Point2


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
DEFAULT_ZOOMS_PER_SEMANTIC_LEVEL = 2


def build_semantic_levels_from_leaf_depths(
    *,
    leaf_depths: Sequence[int],
    zooms_per_level: int = DEFAULT_ZOOMS_PER_SEMANTIC_LEVEL,
) -> tuple[SemanticLevelDefinition, ...]:
    if not leaf_depths:
        return ()

    if zooms_per_level <= 0:
        raise ValueError("zooms_per_level must be positive.")

    occupied_taxonomy_depths = sorted(
        {taxonomy_depth for leaf_depth in leaf_depths for taxonomy_depth in range(leaf_depth + 1)}
    )
    max_leaf_depth = max(leaf_depths)
    levels: list[SemanticLevelDefinition] = []

    for depth_index, taxonomy_depth in enumerate(occupied_taxonomy_depths):
        is_terminal_taxonomy_depth = taxonomy_depth == max_leaf_depth
        min_zoom = depth_index * zooms_per_level
        levels.append(
            SemanticLevelDefinition(
                level=taxonomy_depth,
                stable_id=f"taxonomy_depth_{taxonomy_depth}",
                display_name=f"Taxonomy D{taxonomy_depth}",
                min_zoom=min_zoom,
                max_zoom=min_zoom + zooms_per_level - 1,
                region_role="taxonomy_region",
                child_content_role=("card" if is_terminal_taxonomy_depth else "taxonomy_region"),
            )
        )

    card_level = max_leaf_depth + 1
    card_level_min_zoom = len(occupied_taxonomy_depths) * zooms_per_level
    levels.append(
        SemanticLevelDefinition(
            level=card_level,
            stable_id="cards",
            display_name="Cards",
            min_zoom=card_level_min_zoom,
            max_zoom=card_level_min_zoom + zooms_per_level - 1,
            region_role="card",
            child_content_role="card",
        )
    )
    return tuple(levels)
