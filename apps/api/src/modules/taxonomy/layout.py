"""
Abstract: Deterministic backend layout builder for taxonomy leaf graph coordinates.
Out of scope: Redis persistence and HTTP response construction.
"""

from __future__ import annotations

from datetime import datetime
from math import cos, sin, sqrt

from modules.taxonomy.dto import (
    TaxonomyLeafLayout,
    TaxonomyLeafLayoutEdge,
    TaxonomyLeafLayoutNode,
    TaxonomyLeafLayoutSlice,
    TaxonomyLeafWorldBounds,
)

TAXONOMY_LEAF_LAYOUT_VERSION = "taxonomy-leaf-layout-v1"
_GOLDEN_ANGLE_RADIANS = 2.399963229728653
_BASE_RADIUS = 48.0
_RADIUS_STEP = 52.0


def build_leaf_layout(
    *,
    nodes: list[TaxonomyLeafLayoutNode],
    edges: list[TaxonomyLeafLayoutEdge],
    generated_at: datetime,
) -> TaxonomyLeafLayout:
    sorted_nodes = sorted(nodes, key=lambda node: node.id)
    positioned_nodes = [
        TaxonomyLeafLayoutNode(
            id=node.id,
            scope=node.scope,
            x=_position_on_spiral(index=index)[0],
            y=_position_on_spiral(index=index)[1],
        )
        for index, node in enumerate(sorted_nodes)
    ]
    positioned_node_ids = {node.id for node in positioned_nodes}
    canonical_edges = _canonical_edges(edges=edges, node_ids=positioned_node_ids)

    return TaxonomyLeafLayout(
        layout_version=TAXONOMY_LEAF_LAYOUT_VERSION,
        generated_at=generated_at,
        world_bounds=_world_bounds(positioned_nodes),
        nodes=positioned_nodes,
        edges=canonical_edges,
    )


def slice_leaf_layout(
    layout: TaxonomyLeafLayout,
    *,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> TaxonomyLeafLayoutSlice:
    requested_bounds = TaxonomyLeafWorldBounds(
        min_x=min_x,
        min_y=min_y,
        max_x=max_x,
        max_y=max_y,
    )
    nodes = [node for node in layout.nodes if min_x <= node.x <= max_x and min_y <= node.y <= max_y]
    node_ids = {node.id for node in nodes}
    edges = [
        edge
        for edge in layout.edges
        if edge.source_node_id in node_ids and edge.target_node_id in node_ids
    ]
    return TaxonomyLeafLayoutSlice(
        layout_version=layout.layout_version,
        requested_bounds=requested_bounds,
        nodes=nodes,
        edges=edges,
    )


def _position_on_spiral(*, index: int) -> tuple[float, float]:
    angle = index * _GOLDEN_ANGLE_RADIANS
    radius = _BASE_RADIUS + sqrt(index + 1) * _RADIUS_STEP
    return (cos(angle) * radius, sin(angle) * radius)


def _canonical_edges(
    *,
    edges: list[TaxonomyLeafLayoutEdge],
    node_ids: set[int],
) -> list[TaxonomyLeafLayoutEdge]:
    edge_by_pair: dict[tuple[int, int], TaxonomyLeafLayoutEdge] = {}
    for edge in edges:
        if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
            continue
        source_node_id = min(edge.source_node_id, edge.target_node_id)
        target_node_id = max(edge.source_node_id, edge.target_node_id)
        pair = (source_node_id, target_node_id)
        edge_by_pair.setdefault(
            pair,
            TaxonomyLeafLayoutEdge(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                strength=edge.strength,
            ),
        )
    return [edge_by_pair[pair] for pair in sorted(edge_by_pair)]


def _world_bounds(nodes: list[TaxonomyLeafLayoutNode]) -> TaxonomyLeafWorldBounds:
    if not nodes:
        return TaxonomyLeafWorldBounds(min_x=0.0, min_y=0.0, max_x=0.0, max_y=0.0)
    return TaxonomyLeafWorldBounds(
        min_x=min(node.x for node in nodes),
        min_y=min(node.y for node in nodes),
        max_x=max(node.x for node in nodes),
        max_y=max(node.y for node in nodes),
    )
