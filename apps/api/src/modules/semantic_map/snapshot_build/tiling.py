"""
Abstract: Slice semantic-map regions, labels, and card points into zoom-level tile payloads.
Out of scope: Embedding projection, taxonomy aggregation, and snapshot publication flow.
"""

from __future__ import annotations

from collections.abc import Sequence

from modules.semantic_map.core.dto import SemanticMapRegionTile
from modules.semantic_map.core.geometry import (
    bounds_intersect,
    point_in_bounds,
    tile_bounds_for_coordinate,
)
from modules.semantic_map.core.types import (
    Bounds4,
    LabelPayload,
    Point2,
    PointPayload,
    RegionPayload,
)
from modules.semantic_map.metadata import SemanticLevelDefinition
from modules.semantic_map.snapshot_build.topology import (
    CardPointRecord,
    TaxonomyRegionRecord,
    region_id_for_taxonomy_node,
)


def _point_to_json(point: Point2) -> list[float]:
    return [point[0], point[1]]


def _tile_index_range(
    *,
    zoom: int,
    world_bounds: Bounds4,
    bbox: Bounds4,
) -> tuple[range, range]:
    width = world_bounds[2] - world_bounds[0]
    height = world_bounds[3] - world_bounds[1]
    tiles_per_axis = 2**zoom
    tile_span_x = width / tiles_per_axis
    tile_span_y = height / tiles_per_axis

    min_tile_x = max(0, int((bbox[0] - world_bounds[0]) // tile_span_x))
    max_tile_x = min(tiles_per_axis - 1, int((bbox[2] - world_bounds[0]) // tile_span_x))
    min_tile_y = max(0, int((bbox[1] - world_bounds[1]) // tile_span_y))
    max_tile_y = min(tiles_per_axis - 1, int((bbox[3] - world_bounds[1]) // tile_span_y))
    return (range(min_tile_x, max_tile_x + 1), range(min_tile_y, max_tile_y + 1))


def _tile_index_for_point(*, zoom: int, world_bounds: Bounds4, point: Point2) -> tuple[int, int]:
    width = world_bounds[2] - world_bounds[0]
    height = world_bounds[3] - world_bounds[1]
    tiles_per_axis = 2**zoom

    x_ratio = 0.5 if width <= 0.0 else (point[0] - world_bounds[0]) / width
    y_ratio = 0.5 if height <= 0.0 else (point[1] - world_bounds[1]) / height

    tile_x = max(0, min(tiles_per_axis - 1, int(x_ratio * tiles_per_axis)))
    tile_y = max(0, min(tiles_per_axis - 1, int(y_ratio * tiles_per_axis)))
    return (tile_x, tile_y)


def build_tiles(
    *,
    region_levels: dict[int, list[TaxonomyRegionRecord]],
    card_points: Sequence[CardPointRecord],
    semantic_levels: Sequence[SemanticLevelDefinition],
    world_bounds: Bounds4,
) -> list[SemanticMapRegionTile]:
    tiles: list[SemanticMapRegionTile] = []

    for level_definition in semantic_levels:
        records = region_levels.get(level_definition.level, [])
        for zoom in range(level_definition.min_zoom, level_definition.max_zoom + 1):
            region_tiles: dict[tuple[int, int], list[RegionPayload]] = {}
            label_tiles: dict[tuple[int, int], list[LabelPayload]] = {}
            point_tiles: dict[tuple[int, int], list[PointPayload]] = {}

            for record in records:
                region_bbox = (
                    record.region.bbox[0],
                    record.region.bbox[1],
                    record.region.bbox[2],
                    record.region.bbox[3],
                )
                tile_x_range, tile_y_range = _tile_index_range(
                    zoom=zoom,
                    world_bounds=world_bounds,
                    bbox=region_bbox,
                )
                for tile_x in tile_x_range:
                    for tile_y in tile_y_range:
                        tile_bounds = tile_bounds_for_coordinate(
                            world_bounds=world_bounds,
                            zoom=zoom,
                            tile_x=tile_x,
                            tile_y=tile_y,
                        )
                        if bounds_intersect(region_bbox, tile_bounds):
                            region_tiles.setdefault((tile_x, tile_y), []).append(record.region)

                for label in record.labels:
                    position = (label.position[0], label.position[1])
                    for tile_x in tile_x_range:
                        for tile_y in tile_y_range:
                            tile_bounds = tile_bounds_for_coordinate(
                                world_bounds=world_bounds,
                                zoom=zoom,
                                tile_x=tile_x,
                                tile_y=tile_y,
                            )
                            if point_in_bounds(position, tile_bounds):
                                label_tiles.setdefault((tile_x, tile_y), []).append(label)
                                break
                        else:
                            continue
                        break

            for point in card_points:
                if level_definition.level <= point.leaf_depth:
                    continue
                tile_x, tile_y = _tile_index_for_point(
                    zoom=zoom,
                    world_bounds=world_bounds,
                    point=point.position,
                )
                point_tiles.setdefault((tile_x, tile_y), []).append(
                    PointPayload(
                        id=f"card:{point.node_id}",
                        node_id=point.node_id,
                        leaf_region_id=region_id_for_taxonomy_node(point.leaf_taxonomy_node_id),
                        title=point.title,
                        position=_point_to_json(point.position),
                    )
                )

            for tile_x, tile_y in sorted(
                region_tiles.keys() | label_tiles.keys() | point_tiles.keys()
            ):
                tile_regions = region_tiles.get((tile_x, tile_y), [])
                tile_labels = label_tiles.get((tile_x, tile_y), [])
                tile_points = sorted(
                    point_tiles.get((tile_x, tile_y), []),
                    key=lambda payload: payload.node_id,
                )
                tile_bounds = tile_bounds_for_coordinate(
                    world_bounds=world_bounds,
                    zoom=zoom,
                    tile_x=tile_x,
                    tile_y=tile_y,
                )
                tiles.append(
                    SemanticMapRegionTile(
                        semantic_level=level_definition.level,
                        tile_z=zoom,
                        tile_x=tile_x,
                        tile_y=tile_y,
                        tile_bounds=tile_bounds,
                        region_count=len(tile_regions),
                        label_count=len(tile_labels),
                        regions=tile_regions,
                        labels=tile_labels,
                        points=tile_points,
                    )
                )

    return tiles
