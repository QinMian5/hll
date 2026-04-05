"""
Abstract: Build taxonomy-backed semantic-map regions and card-point records from projected nodes.
Out of scope: 2D projection math, tile slicing, and snapshot publication orchestration.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from modules.knowledge_graph.dto import SemanticMapProjectionNode
from modules.semantic_map.geometry import build_cluster_hull, compute_bbox, compute_centroid
from modules.semantic_map.metadata import SemanticLevelDefinition
from modules.semantic_map.types import Bounds4, LabelPayload, Point2, RegionPayload
from modules.taxonomy.dto import TaxonomyNodeRecord, TaxonomySemanticMapAssignment


@dataclass(frozen=True, slots=True)
class TaxonomyRegionRecord:
    region: RegionPayload
    labels: list[LabelPayload]


@dataclass(frozen=True, slots=True)
class CardPointRecord:
    node_id: int
    title: str
    position: Point2
    leaf_taxonomy_node_id: int
    leaf_depth: int


def _point_to_json(point: Point2) -> list[float]:
    return [point[0], point[1]]


def _bounds_to_json(bounds: Bounds4) -> list[float]:
    return [bounds[0], bounds[1], bounds[2], bounds[3]]


def region_id_for_taxonomy_node(taxonomy_node_id: int) -> str:
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


def build_taxonomy_region_levels(
    *,
    projection_nodes: Sequence[SemanticMapProjectionNode],
    projected_points: Sequence[Point2],
    taxonomy_nodes: Sequence[TaxonomyNodeRecord],
    assignments: Sequence[TaxonomySemanticMapAssignment],
    semantic_levels: Sequence[SemanticLevelDefinition],
) -> tuple[dict[int, list[TaxonomyRegionRecord]], list[CardPointRecord]]:
    projection_index_by_node_id: dict[int, int] = {
        node.node_id: index for index, node in enumerate(projection_nodes)
    }
    taxonomy_nodes_by_id: dict[int, TaxonomyNodeRecord] = {node.id: node for node in taxonomy_nodes}
    child_ids_by_parent: dict[int, list[int]] = defaultdict(list)
    for taxonomy_node in taxonomy_nodes:
        if taxonomy_node.parent_id is not None:
            child_ids_by_parent[taxonomy_node.parent_id].append(taxonomy_node.id)

    member_indexes_by_taxonomy_node_id: dict[int, set[int]] = {}
    card_points: list[CardPointRecord] = []
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
            CardPointRecord(
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

    region_levels: dict[int, list[TaxonomyRegionRecord]] = {}
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

        level_regions: list[TaxonomyRegionRecord] = []
        for display_rank, taxonomy_node in enumerate(sorted_depth_nodes, start=1):
            member_indexes = sorted(member_indexes_by_taxonomy_node_id[taxonomy_node.id])
            member_points = [projected_points[index] for index in member_indexes]
            centroid = compute_centroid(member_points)
            bbox = compute_bbox(member_points)
            region_id = region_id_for_taxonomy_node(taxonomy_node.id)
            parent_region_id = (
                region_id_for_taxonomy_node(taxonomy_node.parent_id)
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
            level_regions.append(TaxonomyRegionRecord(region=region, labels=labels))

        region_levels[level_definition.level] = level_regions

    return region_levels, sorted(card_points, key=lambda point: point.node_id)
