"""
Abstract: Semantic-map rebuild orchestration from knowledge-graph embeddings to snapshot tiles.
Out of scope: FastAPI transport wiring and SQLAlchemy query execution details.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil

import numpy as np
from sklearn.cluster import AgglomerativeClustering
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
    DEFAULT_PHASE1_SEMANTIC_LEVELS,
    DEFAULT_TILE_SIZE,
    DEFAULT_VIEW_TARGET,
    WORLD_BOUNDS,
    SemanticLevelDefinition,
)
from modules.semantic_map.ports import SemanticMapSnapshotWritePort
from modules.semantic_map.types import Bounds4, LabelPayload, Point2, RegionPayload


@dataclass(frozen=True, slots=True)
class _ClusterRecord:
    region_id: str
    members: frozenset[int]
    region: RegionPayload
    labels: list[LabelPayload]


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


def _resolve_target_cluster_counts(
    *,
    total_nodes: int,
    semantic_levels: Sequence[SemanticLevelDefinition],
) -> list[int]:
    if len(semantic_levels) == 1:
        return [1]

    counts = [1]
    last_level_index = len(semantic_levels) - 1
    for level_index in range(1, len(semantic_levels)):
        if level_index == last_level_index:
            counts.append(total_nodes)
            continue

        ratio = level_index / last_level_index
        target_count = min(total_nodes, ceil(total_nodes**ratio))
        counts.append(max(counts[-1], target_count))
    return counts


def _clusters_for_target_count(
    *,
    children: np.ndarray,
    sample_count: int,
    target_cluster_count: int,
) -> list[tuple[int, ...]]:
    if target_cluster_count >= sample_count:
        return [(index,) for index in range(sample_count)]

    members: dict[int, tuple[int, ...]] = {index: (index,) for index in range(sample_count)}
    active_cluster_ids = set(range(sample_count))
    merges_to_apply = sample_count - target_cluster_count

    for merge_index, merge in enumerate(children[:merges_to_apply]):
        left = int(merge[0])
        right = int(merge[1])
        cluster_id = sample_count + merge_index
        merged_members = tuple(sorted((*members[left], *members[right])))
        members[cluster_id] = merged_members
        active_cluster_ids.remove(left)
        active_cluster_ids.remove(right)
        active_cluster_ids.add(cluster_id)

    return sorted(
        (members[cluster_id] for cluster_id in active_cluster_ids),
        key=lambda cluster_members: (-len(cluster_members), cluster_members),
    )


def _build_cluster_levels(
    *,
    nodes: Sequence[SemanticMapProjectionNode],
    semantic_levels: Sequence[SemanticLevelDefinition],
) -> list[list[tuple[int, ...]]]:
    if len(nodes) == 1:
        singleton_cluster: tuple[int, ...] = (0,)
        return [[singleton_cluster] for _ in semantic_levels]

    matrix = np.asarray([node.embedding for node in nodes], dtype=float)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=0,
        compute_distances=True,
    )
    clustering.fit(matrix)

    target_cluster_counts = _resolve_target_cluster_counts(
        total_nodes=len(nodes),
        semantic_levels=semantic_levels,
    )
    return [
        _clusters_for_target_count(
            children=clustering.children_,
            sample_count=len(nodes),
            target_cluster_count=target_cluster_count,
        )
        for target_cluster_count in target_cluster_counts
    ]


def _point_to_json(point: Point2) -> list[float]:
    return [point[0], point[1]]


def _bounds_to_json(bounds: Bounds4) -> list[float]:
    return [bounds[0], bounds[1], bounds[2], bounds[3]]


def _build_region_name(nodes: Sequence[SemanticMapProjectionNode]) -> str:
    titles = [node.title for node in nodes[:2]]
    return " · ".join(titles)


def _build_region_levels(
    *,
    nodes: Sequence[SemanticMapProjectionNode],
    projected_points: Sequence[Point2],
    semantic_levels: Sequence[SemanticLevelDefinition],
) -> dict[int, list[_ClusterRecord]]:
    cluster_levels = _build_cluster_levels(nodes=nodes, semantic_levels=semantic_levels)
    region_levels: dict[int, list[_ClusterRecord]] = {}
    previous_level_records: list[_ClusterRecord] = []

    for level_index, level_definition in enumerate(semantic_levels):
        next_clusters = (
            cluster_levels[level_index + 1] if level_index + 1 < len(cluster_levels) else []
        )
        current_records: list[_ClusterRecord] = []

        for display_rank, members in enumerate(cluster_levels[level_index], start=1):
            member_set = frozenset(members)
            member_nodes = [nodes[index] for index in members]
            member_points = [projected_points[index] for index in members]
            parent_id = next(
                (
                    record.region_id
                    for record in previous_level_records
                    if member_set.issubset(record.members)
                ),
                None,
            )
            children_available = any(
                frozenset(next_members) < member_set for next_members in next_clusters
            )
            region_id = f"{level_definition.stable_id}:{display_rank}"
            centroid = compute_centroid(member_points)
            bbox = compute_bbox(member_points)
            region = RegionPayload(
                id=region_id,
                parent_id=parent_id,
                region_name=_build_region_name(member_nodes),
                centroid=_point_to_json(centroid),
                bbox=_bounds_to_json(bbox),
                geometry=build_cluster_hull(member_points),
                display_rank=display_rank,
                children_available=children_available,
            )
            labels: list[LabelPayload] = [
                LabelPayload(
                    id=f"{region_id}:label:1",
                    region_id=region_id,
                    text=member_nodes[0].title,
                    position=_point_to_json(centroid),
                    label_rank=display_rank,
                    font_size=max(14, 22 - level_definition.level * 3),
                )
            ]
            current_records.append(
                _ClusterRecord(
                    region_id=region_id,
                    members=member_set,
                    region=region,
                    labels=labels,
                )
            )

        region_levels[level_definition.level] = current_records
        previous_level_records = current_records

    return region_levels


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


def _build_tiles(
    *,
    region_levels: dict[int, list[_ClusterRecord]],
    semantic_levels: Sequence[SemanticLevelDefinition],
    world_bounds: Bounds4,
) -> list[SemanticMapRegionTile]:
    tiles: list[SemanticMapRegionTile] = []

    for level_definition in semantic_levels:
        records = region_levels[level_definition.level]
        for zoom in range(level_definition.min_zoom, level_definition.max_zoom + 1):
            region_tiles: dict[tuple[int, int], list[RegionPayload]] = {}
            label_tiles: dict[tuple[int, int], list[LabelPayload]] = {}

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

            for tile_x, tile_y in sorted(region_tiles.keys() | label_tiles.keys()):
                tile_regions = region_tiles.get((tile_x, tile_y), [])
                tile_labels = label_tiles.get((tile_x, tile_y), [])
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
                    )
                )

    return tiles


class SemanticMapRebuildService:
    def __init__(
        self,
        *,
        projection_port: KnowledgeGraphProjectionPort,
        snapshot_repo: SemanticMapSnapshotWritePort,
        now: Callable[[], datetime] = _utc_now,
        semantic_levels: Sequence[SemanticLevelDefinition] = DEFAULT_PHASE1_SEMANTIC_LEVELS,
    ) -> None:
        self._projection_port = projection_port
        self._snapshot_repo = snapshot_repo
        self._now = now
        self._semantic_levels = tuple(semantic_levels)

    async def rebuild_current_snapshot(self) -> str | None:
        nodes = await self._projection_port.list_projection_nodes_for_semantic_map()
        if not nodes:
            return None

        built_at = self._now()
        version = _snapshot_version_from_datetime(built_at)
        projected_points = _project_points(nodes)
        region_levels = _build_region_levels(
            nodes=nodes,
            projected_points=projected_points,
            semantic_levels=self._semantic_levels,
        )
        tiles = _build_tiles(
            region_levels=region_levels,
            semantic_levels=self._semantic_levels,
            world_bounds=WORLD_BOUNDS,
        )
        manifest = SemanticMapManifest(
            version=version,
            schema_version=version,
            built_at=built_at,
            world_bounds=WORLD_BOUNDS,
            tile_size=DEFAULT_TILE_SIZE,
            max_zoom=max(level.max_zoom for level in self._semantic_levels),
            default_view=DefaultView(target=DEFAULT_VIEW_TARGET, zoom=0.0),
            default_semantic_level=self._semantic_levels[0].level,
        )
        await self._snapshot_repo.publish_snapshot(
            manifest=manifest,
            tiles=tiles,
        )
        return version
