"""
Abstract: Deterministic backend layout builder for taxonomy leaf graph coordinates.
Out of scope: Redis persistence and HTTP response construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import cos, sin, sqrt
from typing import Literal

from modules.taxonomy.dto import (
    TaxonomyLeafLayout,
    TaxonomyLeafLayoutEdge,
    TaxonomyLeafLayoutNode,
    TaxonomyLeafLayoutSlice,
    TaxonomyLeafWorldBounds,
)

TAXONOMY_LEAF_LAYOUT_VERSION = "taxonomy-leaf-layout-v3"
_GOLDEN_ANGLE_RADIANS = 2.399963229728653
_BASE_RADIUS = 96.0
_RADIUS_STEP = 104.0
_SIMULATION_TICKS = 220
_ALPHA_MIN = 0.001
_ALPHA_DECAY = 1 - _ALPHA_MIN ** (1 / 300)
_VELOCITY_RETENTION = 0.6
_LINK_BASE_DISTANCE = 192.0
_LINK_DISTANCE_STRENGTH_FACTOR = 64.0
_LINK_BASE_STRENGTH = 0.38
_LINK_STRENGTH_FACTOR = 0.34
_CHARGE_STRENGTH = -320.0
_COLLISION_RADIUS = 20.0
_COLLISION_STRENGTH = 1.0
_CENTER_X = 0.0
_CENTER_Y = 0.0
_CENTER_STRENGTH = 0.12


@dataclass
class _SimulationNode:
    id: int
    scope: Literal["inner", "outer"]
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0


def build_leaf_layout(
    *,
    nodes: list[TaxonomyLeafLayoutNode],
    edges: list[TaxonomyLeafLayoutEdge],
    generated_at: datetime,
) -> TaxonomyLeafLayout:
    sorted_nodes = sorted(nodes, key=lambda node: node.id)
    simulation_nodes = [
        _build_simulation_node(node=node, index=index) for index, node in enumerate(sorted_nodes)
    ]
    positioned_node_ids = {node.id for node in simulation_nodes}
    canonical_edges = _canonical_edges(edges=edges, node_ids=positioned_node_ids)
    _run_force_simulation(nodes=simulation_nodes, edges=canonical_edges)
    positioned_nodes = [
        TaxonomyLeafLayoutNode(
            id=node.id,
            scope=node.scope,
            x=round(node.x, 6),
            y=round(node.y, 6),
        )
        for node in simulation_nodes
    ]

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


def _build_simulation_node(
    *,
    index: int,
    node: TaxonomyLeafLayoutNode,
) -> _SimulationNode:
    x, y = _position_on_spiral(index=index)
    return _SimulationNode(id=node.id, scope=node.scope, x=x, y=y)


def _run_force_simulation(
    *,
    nodes: list[_SimulationNode],
    edges: list[TaxonomyLeafLayoutEdge],
) -> None:
    if len(nodes) <= 1:
        return

    nodes_by_id = {node.id: node for node in nodes}
    alpha = 1.0

    for _ in range(_SIMULATION_TICKS):
        alpha += (0.0 - alpha) * _ALPHA_DECAY
        _apply_link_force(nodes_by_id=nodes_by_id, edges=edges, alpha=alpha)
        _apply_charge_force(nodes=nodes, alpha=alpha)
        _apply_collision_force(nodes=nodes, alpha=alpha)
        _apply_center_force(nodes=nodes)

        for node in nodes:
            node.vx *= _VELOCITY_RETENTION
            node.vy *= _VELOCITY_RETENTION
            node.x += node.vx
            node.y += node.vy


def _apply_link_force(
    *,
    alpha: float,
    edges: list[TaxonomyLeafLayoutEdge],
    nodes_by_id: dict[int, _SimulationNode],
) -> None:
    for edge in edges:
        source = nodes_by_id[edge.source_node_id]
        target = nodes_by_id[edge.target_node_id]
        dx = (target.x + target.vx) - (source.x + source.vx)
        dy = (target.y + target.vy) - (source.y + source.vy)
        distance = sqrt(dx * dx + dy * dy)
        if distance == 0.0:
            dx, dy, distance = _deterministic_unit_vector(
                source_node_id=source.id,
                target_node_id=target.id,
            )

        target_distance = _LINK_BASE_DISTANCE - edge.strength * _LINK_DISTANCE_STRENGTH_FACTOR
        link_strength = _LINK_BASE_STRENGTH + edge.strength * _LINK_STRENGTH_FACTOR
        force = (distance - target_distance) / distance * alpha * link_strength
        offset_x = dx * force * 0.5
        offset_y = dy * force * 0.5
        source.vx += offset_x
        source.vy += offset_y
        target.vx -= offset_x
        target.vy -= offset_y


def _apply_charge_force(
    *,
    alpha: float,
    nodes: list[_SimulationNode],
) -> None:
    for left_index, source in enumerate(nodes):
        for target in nodes[left_index + 1 :]:
            dx = target.x - source.x
            dy = target.y - source.y
            distance_squared = dx * dx + dy * dy
            if distance_squared == 0.0:
                dx, dy, distance_squared = _deterministic_unit_vector(
                    source_node_id=source.id,
                    target_node_id=target.id,
                )

            distance_squared = max(distance_squared, 1.0)
            force = _CHARGE_STRENGTH * alpha / distance_squared
            offset_x = dx * force
            offset_y = dy * force
            source.vx += offset_x
            source.vy += offset_y
            target.vx -= offset_x
            target.vy -= offset_y


def _apply_collision_force(
    *,
    alpha: float,
    nodes: list[_SimulationNode],
) -> None:
    minimum_distance = _COLLISION_RADIUS * 2
    for left_index, source in enumerate(nodes):
        for target in nodes[left_index + 1 :]:
            dx = (target.x + target.vx) - (source.x + source.vx)
            dy = (target.y + target.vy) - (source.y + source.vy)
            distance = sqrt(dx * dx + dy * dy)
            if distance == 0.0:
                dx, dy, distance = _deterministic_unit_vector(
                    source_node_id=source.id,
                    target_node_id=target.id,
                )

            if distance >= minimum_distance:
                continue

            force = (minimum_distance - distance) / distance * _COLLISION_STRENGTH * alpha
            offset_x = dx * force * 0.5
            offset_y = dy * force * 0.5
            source.vx -= offset_x
            source.vy -= offset_y
            target.vx += offset_x
            target.vy += offset_y


def _apply_center_force(nodes: list[_SimulationNode]) -> None:
    center_x = sum(node.x for node in nodes) / len(nodes)
    center_y = sum(node.y for node in nodes) / len(nodes)
    offset_x = (center_x - _CENTER_X) * _CENTER_STRENGTH
    offset_y = (center_y - _CENTER_Y) * _CENTER_STRENGTH

    for node in nodes:
        node.x -= offset_x
        node.y -= offset_y


def _deterministic_unit_vector(
    *,
    source_node_id: int,
    target_node_id: int,
) -> tuple[float, float, float]:
    angle = (source_node_id * 31 + target_node_id * 17) * _GOLDEN_ANGLE_RADIANS
    return (cos(angle), sin(angle), 1.0)


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
