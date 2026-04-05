"""
Abstract: Semantic-map rebuild orchestration from knowledge-graph embeddings to snapshot tiles.
Out of scope: FastAPI transport wiring and SQLAlchemy query execution details.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from sklearn.decomposition import PCA

from modules.knowledge_graph.dto import SemanticMapProjectionNode
from modules.knowledge_graph.ports import KnowledgeGraphProjectionPort
from modules.semantic_map.dto import DefaultView, SemanticMapManifest, SemanticMapRegionTile
from modules.semantic_map.geometry import (
    bounds_intersect,
    build_cluster_hull,
    compute_bbox,
    compute_centroid,
    point_in_bounds,
    tile_bounds_for_coordinate,
)
from modules.semantic_map.metadata import (
    DEFAULT_TILE_SIZE,
    DEFAULT_VIEW_TARGET,
    WORLD_BOUNDS,
    SemanticLevelDefinition,
    build_semantic_levels_from_leaf_depths,
)
from modules.semantic_map.ports import SemanticMapSnapshotWritePort, TaxonomyAssignedNodesPort
from modules.semantic_map.types import (
    Bounds4,
    LabelPayload,
    Point2,
    PointPayload,
    RegionPayload,
)
from modules.taxonomy.dto import TaxonomyNodeRecord, TaxonomySemanticMapAssignment


@dataclass(frozen=True, slots=True)
class _TaxonomyRegionRecord:
    region: RegionPayload
    labels: list[LabelPayload]


@dataclass(frozen=True, slots=True)
class _CardPointRecord:
    node_id: int
    title: str
    position: Point2
    leaf_taxonomy_node_id: int
    leaf_depth: int


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _snapshot_version_from_datetime(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y%m%d_%H%M%S_%f")


def _normalize_projected_points(points: Sequence[Point2]) -> list[Point2]:
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)

    def _scale(value: float, *, lower: float, upper: float) -> float:
        if upper == lower:
            return 500.0
        return 100.0 + ((value - lower) / (upper - lower)) * 800.0

    return [
        (
            _scale(point[0], lower=min_x, upper=max_x),
            _scale(point[1], lower=min_y, upper=max_y),
        )
        for point in points
    ]


def _project_points(nodes: Sequence[SemanticMapProjectionNode]) -> list[Point2]:
    if len(nodes) == 1:
        return [(500.0, 500.0)]

    matrix = np.asarray([node.embedding for node in nodes], dtype=float)
    projected = PCA(n_components=2).fit_transform(matrix)
    return _normalize_projected_points([(float(row[0]), float(row[1])) for row in projected])


def _point_to_json(point: Point2) -> list[float]:
    return [point[0], point[1]]


def _bounds_to_json(bounds: Bounds4) -> list[float]:
    return [bounds[0], bounds[1], bounds[2], bounds[3]]


def _region_id_for_taxonomy_node(taxonomy_node_id: int) -> str:
    return f"taxonomy:{taxonomy_node_id}"


def _collect_ancestor_ids(
    *,
    taxonomy_node_id: int,
    taxonomy_nodes_by_id: dict[int, TaxonomyNodeRecord],
) -> tuple[int, ...]:
    ancestor_ids: list[int] = []
    visited: set[int] = set()
    current_node_id: int | None = taxonomy_node_id

    while (
        current_node_id is not None
        and current_node_id not in visited
        and current_node_id in taxonomy_nodes_by_id
    ):
        visited.add(current_node_id)
        ancestor_ids.append(current_node_id)
        current_node_id = taxonomy_nodes_by_id[current_node_id].parent_id

    return tuple(ancestor_ids)


def _build_taxonomy_region_levels(
    *,
    projection_nodes: Sequence[SemanticMapProjectionNode],
    projected_points: Sequence[Point2],
    taxonomy_nodes: Sequence[TaxonomyNodeRecord],
    assignments: Sequence[TaxonomySemanticMapAssignment],
    semantic_levels: Sequence[SemanticLevelDefinition],
) -> tuple[dict[int, list[_TaxonomyRegionRecord]], list[_CardPointRecord]]:
    projection_index_by_node_id: dict[int, int] = {
        node.node_id: index for index, node in enumerate(projection_nodes)
    }
    taxonomy_nodes_by_id: dict[int, TaxonomyNodeRecord] = {node.id: node for node in taxonomy_nodes}
    child_ids_by_parent: dict[int, list[int]] = defaultdict(list)
    for taxonomy_node in taxonomy_nodes:
        if taxonomy_node.parent_id is not None:
            child_ids_by_parent[taxonomy_node.parent_id].append(taxonomy_node.id)

    member_indexes_by_taxonomy_node_id: dict[int, set[int]] = {}
    card_points: list[_CardPointRecord] = []
    for assignment in assignments:
        projection_index = projection_index_by_node_id.get(assignment.node_id)
        if projection_index is None:
            continue
        leaf_node = taxonomy_nodes_by_id.get(assignment.taxonomy_leaf_id)
        if leaf_node is None or not leaf_node.is_leaf:
            continue

        projection_node = projection_nodes[projection_index]
        point = projected_points[projection_index]
        card_points.append(
            _CardPointRecord(
                node_id=projection_node.node_id,
                title=projection_node.title,
                position=point,
                leaf_taxonomy_node_id=leaf_node.id,
                leaf_depth=leaf_node.depth,
            )
        )
        for ancestor_id in _collect_ancestor_ids(
            taxonomy_node_id=leaf_node.id,
            taxonomy_nodes_by_id=taxonomy_nodes_by_id,
        ):
            member_indexes_by_taxonomy_node_id.setdefault(ancestor_id, set()).add(projection_index)

    region_levels: dict[int, list[_TaxonomyRegionRecord]] = {}
    for level_definition in semantic_levels:
        if level_definition.region_role == "card":
            region_levels[level_definition.level] = []
            continue

        depth_nodes = [
            node
            for node in taxonomy_nodes
            if node.depth == level_definition.level
            and node.id in member_indexes_by_taxonomy_node_id
        ]
        sorted_depth_nodes = sorted(
            depth_nodes,
            key=lambda node: (
                -len(member_indexes_by_taxonomy_node_id[node.id]),
                node.name,
                node.id,
            ),
        )

        level_regions: list[_TaxonomyRegionRecord] = []
        for display_rank, taxonomy_node in enumerate(sorted_depth_nodes, start=1):
            member_indexes = sorted(member_indexes_by_taxonomy_node_id[taxonomy_node.id])
            member_points = [projected_points[index] for index in member_indexes]
            centroid = compute_centroid(member_points)
            bbox = compute_bbox(member_points)
            region_id = _region_id_for_taxonomy_node(taxonomy_node.id)
            parent_region_id = (
                _region_id_for_taxonomy_node(taxonomy_node.parent_id)
                if taxonomy_node.parent_id is not None
                and taxonomy_node.parent_id in member_indexes_by_taxonomy_node_id
                else None
            )
            children_available = any(
                child_id in member_indexes_by_taxonomy_node_id
                for child_id in child_ids_by_parent.get(taxonomy_node.id, [])
            )
            region = RegionPayload(
                id=region_id,
                parent_id=parent_region_id,
                region_name=taxonomy_node.name,
                centroid=_point_to_json(centroid),
                bbox=_bounds_to_json(bbox),
                geometry=build_cluster_hull(member_points),
                display_rank=display_rank,
                children_available=children_available,
            )
            labels = [
                LabelPayload(
                    id=f"{region_id}:label:1",
                    region_id=region_id,
                    text=taxonomy_node.name,
                    position=_point_to_json(centroid),
                    label_rank=display_rank,
                    font_size=max(14, 22 - level_definition.level * 3),
                )
            ]
            level_regions.append(_TaxonomyRegionRecord(region=region, labels=labels))

        region_levels[level_definition.level] = level_regions

    return region_levels, sorted(card_points, key=lambda point: point.node_id)


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


def _build_tiles(
    *,
    region_levels: dict[int, list[_TaxonomyRegionRecord]],
    card_points: Sequence[_CardPointRecord],
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
                        leaf_region_id=_region_id_for_taxonomy_node(point.leaf_taxonomy_node_id),
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


class SemanticMapRebuildService:
    def __init__(
        self,
        *,
        projection_port: KnowledgeGraphProjectionPort,
        taxonomy_port: TaxonomyAssignedNodesPort,
        snapshot_repo: SemanticMapSnapshotWritePort,
        now: Callable[[], datetime] = _utc_now,
        semantic_levels: Sequence[SemanticLevelDefinition] | None = None,
    ) -> None:
        self._projection_port = projection_port
        self._taxonomy_port = taxonomy_port
        self._snapshot_repo = snapshot_repo
        self._now = now
        self._semantic_levels = tuple(semantic_levels) if semantic_levels is not None else None

    async def rebuild_current_snapshot(self) -> str | None:
        assignments = await self._taxonomy_port.list_semantic_map_assignments()
        if not assignments:
            return None

        semantic_levels = await self._resolve_semantic_levels()
        if not semantic_levels:
            return None

        assigned_node_ids = sorted({assignment.node_id for assignment in assignments})
        nodes = await self._projection_port.list_projection_nodes_for_node_ids(
            node_ids=assigned_node_ids,
        )
        if not nodes:
            return None
        ordered_nodes = sorted(nodes, key=lambda node: node.node_id)

        taxonomy_nodes = await self._taxonomy_port.list_tree_nodes_for_semantic_map()
        if not taxonomy_nodes:
            return None

        built_at = self._now()
        version = _snapshot_version_from_datetime(built_at)
        projected_points = _project_points(ordered_nodes)
        region_levels, card_points = _build_taxonomy_region_levels(
            projection_nodes=ordered_nodes,
            projected_points=projected_points,
            taxonomy_nodes=taxonomy_nodes,
            assignments=assignments,
            semantic_levels=semantic_levels,
        )
        if not card_points:
            return None
        tiles = _build_tiles(
            region_levels=region_levels,
            card_points=card_points,
            semantic_levels=semantic_levels,
            world_bounds=WORLD_BOUNDS,
        )
        manifest = SemanticMapManifest(
            version=version,
            schema_version=version,
            built_at=built_at,
            world_bounds=WORLD_BOUNDS,
            tile_size=DEFAULT_TILE_SIZE,
            max_zoom=max(level.max_zoom for level in semantic_levels),
            default_view=DefaultView(target=DEFAULT_VIEW_TARGET, zoom=0.0),
            default_semantic_level=semantic_levels[0].level,
        )
        await self._snapshot_repo.publish_snapshot(
            manifest=manifest,
            tiles=tiles,
        )
        return version

    async def _resolve_semantic_levels(self) -> tuple[SemanticLevelDefinition, ...]:
        if self._semantic_levels is not None:
            return self._semantic_levels

        leaf_depths = await self._taxonomy_port.list_assigned_leaf_depths_for_semantic_map()
        return build_semantic_levels_from_leaf_depths(leaf_depths=leaf_depths)
