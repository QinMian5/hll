"""
Abstract: Deterministic backend layout builder for taxonomy card-scope graph coordinates.
Out of scope: Redis persistence and HTTP response construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import cos, isfinite, sin, sqrt
from typing import Literal

from modules.taxonomy.dto import (
    TaxonomyCardScopeLayout,
    TaxonomyCardScopeLayoutEdge,
    TaxonomyCardScopeLayoutNode,
    TaxonomyCardScopeLayoutSlice,
    TaxonomyCardScopeWorldBounds,
)

TAXONOMY_CARD_SCOPE_LAYOUT_VERSION = "taxonomy-card-scope-layout-v2"
_GOLDEN_ANGLE_RADIANS = 2.399963229728653
_BASE_RADIUS = 80.0
_RADIUS_STEP = 96.0
_SIMULATION_TICKS = 160
_ALPHA_MIN = 0.001
_ALPHA_DECAY = 1 - _ALPHA_MIN ** (1 / 300)
_VELOCITY_RETENTION = 0.55
_LINK_BASE_DISTANCE = 92.0
_LINK_DISTANCE_STRENGTH_FACTOR = 36.0
_LINK_BASE_STRENGTH = 1.05
_LINK_STRENGTH_FACTOR = 0.5
_CHARGE_STRENGTH = -180.0
_COLLISION_RADIUS = 16.0
_COLLISION_STRENGTH = 0.92
_CENTER_X = 0.0
_CENTER_Y = 0.0
_CENTER_STRENGTH = 0.10
_RADIAL_BOUNDARY_RADIUS = 0.0
_RADIAL_BOUNDARY_STRENGTH = 0.0


@dataclass(frozen=True)
class TaxonomyCardScopeLayoutParams:
    seed_base_radius: float = _BASE_RADIUS
    seed_radius_step: float = _RADIUS_STEP
    simulation_ticks: int = _SIMULATION_TICKS
    alpha_min: float = _ALPHA_MIN
    velocity_retention: float = _VELOCITY_RETENTION
    link_base_distance: float = _LINK_BASE_DISTANCE
    link_distance_strength_factor: float = _LINK_DISTANCE_STRENGTH_FACTOR
    link_base_strength: float = _LINK_BASE_STRENGTH
    link_strength_factor: float = _LINK_STRENGTH_FACTOR
    charge_strength: float = _CHARGE_STRENGTH
    collision_radius: float = _COLLISION_RADIUS
    collision_strength: float = _COLLISION_STRENGTH
    center_gravity_strength: float = _CENTER_STRENGTH
    radial_boundary_radius: float = _RADIAL_BOUNDARY_RADIUS
    radial_boundary_strength: float = _RADIAL_BOUNDARY_STRENGTH

    def __post_init__(self) -> None:
        _validate_non_negative_integer("simulation_ticks", self.simulation_ticks)
        _validate_fraction_exclusive("alpha_min", self.alpha_min)
        _validate_fraction_inclusive("velocity_retention", self.velocity_retention)
        _validate_non_negative_number("seed_base_radius", self.seed_base_radius)
        _validate_non_negative_number("seed_radius_step", self.seed_radius_step)
        _validate_non_negative_number("link_base_distance", self.link_base_distance)
        _validate_number("link_distance_strength_factor", self.link_distance_strength_factor)
        _validate_number("link_base_strength", self.link_base_strength)
        _validate_number("link_strength_factor", self.link_strength_factor)
        _validate_number("charge_strength", self.charge_strength)
        _validate_non_negative_number("collision_radius", self.collision_radius)
        _validate_non_negative_number("collision_strength", self.collision_strength)
        _validate_non_negative_number("center_gravity_strength", self.center_gravity_strength)
        _validate_non_negative_number("radial_boundary_radius", self.radial_boundary_radius)
        _validate_non_negative_number("radial_boundary_strength", self.radial_boundary_strength)

    @property
    def alpha_decay(self) -> float:
        return 1 - self.alpha_min ** (1 / 300)


@dataclass
class _SimulationNode:
    id: int
    scope: Literal["inner", "outer"]
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0


def build_card_scope_layout(
    *,
    nodes: list[TaxonomyCardScopeLayoutNode],
    edges: list[TaxonomyCardScopeLayoutEdge],
    generated_at: datetime,
    params: TaxonomyCardScopeLayoutParams | None = None,
) -> TaxonomyCardScopeLayout:
    layout_params = params or TAXONOMY_CARD_SCOPE_LAYOUT_PRODUCTION_PARAMS
    sorted_nodes = sorted(nodes, key=lambda node: node.id)
    simulation_nodes = [
        _build_simulation_node(node=node, index=index, params=layout_params)
        for index, node in enumerate(sorted_nodes)
    ]
    positioned_node_ids = {node.id for node in simulation_nodes}
    canonical_edges = _canonical_edges(edges=edges, node_ids=positioned_node_ids)
    _run_force_simulation(nodes=simulation_nodes, edges=canonical_edges, params=layout_params)
    positioned_nodes = [
        TaxonomyCardScopeLayoutNode(
            id=node.id,
            scope=node.scope,
            x=round(node.x, 6),
            y=round(node.y, 6),
        )
        for node in simulation_nodes
    ]

    return TaxonomyCardScopeLayout(
        layout_version=TAXONOMY_CARD_SCOPE_LAYOUT_VERSION,
        generated_at=generated_at,
        world_bounds=_world_bounds(positioned_nodes),
        nodes=positioned_nodes,
        edges=canonical_edges,
    )


def slice_card_scope_layout(
    layout: TaxonomyCardScopeLayout,
    *,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> TaxonomyCardScopeLayoutSlice:
    requested_bounds = TaxonomyCardScopeWorldBounds(
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
    return TaxonomyCardScopeLayoutSlice(
        layout_version=layout.layout_version,
        requested_bounds=requested_bounds,
        nodes=nodes,
        edges=edges,
    )


def _position_on_spiral(
    *, index: int, params: TaxonomyCardScopeLayoutParams
) -> tuple[float, float]:
    angle = index * _GOLDEN_ANGLE_RADIANS
    radius = params.seed_base_radius + sqrt(index + 1) * params.seed_radius_step
    return (cos(angle) * radius, sin(angle) * radius)


def _build_simulation_node(
    *,
    index: int,
    node: TaxonomyCardScopeLayoutNode,
    params: TaxonomyCardScopeLayoutParams,
) -> _SimulationNode:
    x, y = _position_on_spiral(index=index, params=params)
    return _SimulationNode(id=node.id, scope=node.scope, x=x, y=y)


def _run_force_simulation(
    *,
    nodes: list[_SimulationNode],
    edges: list[TaxonomyCardScopeLayoutEdge],
    params: TaxonomyCardScopeLayoutParams,
) -> None:
    if len(nodes) <= 1:
        return

    nodes_by_id = {node.id: node for node in nodes}
    alpha = 1.0

    for _ in range(params.simulation_ticks):
        alpha += (0.0 - alpha) * params.alpha_decay
        _apply_link_force(nodes_by_id=nodes_by_id, edges=edges, alpha=alpha, params=params)
        _apply_charge_force(nodes=nodes, alpha=alpha, params=params)
        _apply_collision_force(nodes=nodes, alpha=alpha, params=params)
        _apply_center_force(nodes=nodes, alpha=alpha, params=params)
        _apply_radial_boundary_force(nodes=nodes, alpha=alpha, params=params)

        for node in nodes:
            node.vx *= params.velocity_retention
            node.vy *= params.velocity_retention
            node.x += node.vx
            node.y += node.vy


def _apply_link_force(
    *,
    alpha: float,
    edges: list[TaxonomyCardScopeLayoutEdge],
    nodes_by_id: dict[int, _SimulationNode],
    params: TaxonomyCardScopeLayoutParams,
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

        target_distance = (
            params.link_base_distance - edge.strength * params.link_distance_strength_factor
        )
        link_strength = params.link_base_strength + edge.strength * params.link_strength_factor
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
    params: TaxonomyCardScopeLayoutParams,
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
            force = params.charge_strength * alpha / distance_squared
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
    params: TaxonomyCardScopeLayoutParams,
) -> None:
    minimum_distance = params.collision_radius * 2
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

            force = (minimum_distance - distance) / distance * params.collision_strength * alpha
            offset_x = dx * force * 0.5
            offset_y = dy * force * 0.5
            source.vx -= offset_x
            source.vy -= offset_y
            target.vx += offset_x
            target.vy += offset_y


def _apply_center_force(
    *,
    nodes: list[_SimulationNode],
    alpha: float,
    params: TaxonomyCardScopeLayoutParams,
) -> None:
    if params.center_gravity_strength == 0.0:
        return

    for node in nodes:
        node.vx += (_CENTER_X - node.x) * params.center_gravity_strength * alpha
        node.vy += (_CENTER_Y - node.y) * params.center_gravity_strength * alpha


def _apply_radial_boundary_force(
    *,
    nodes: list[_SimulationNode],
    alpha: float,
    params: TaxonomyCardScopeLayoutParams,
) -> None:
    if params.radial_boundary_radius == 0.0 or params.radial_boundary_strength == 0.0:
        return

    for node in nodes:
        dx = node.x - _CENTER_X
        dy = node.y - _CENTER_Y
        distance = sqrt(dx * dx + dy * dy)
        if distance <= params.radial_boundary_radius or distance == 0.0:
            continue

        force = (
            (distance - params.radial_boundary_radius)
            / distance
            * params.radial_boundary_strength
            * alpha
        )
        node.vx -= dx * force
        node.vy -= dy * force


def _validate_number(name: str, value: float) -> None:
    if not isfinite(value):
        raise ValueError(f"{name} must be finite.")


def _validate_non_negative_number(name: str, value: float) -> None:
    _validate_number(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative.")


def _validate_non_negative_integer(name: str, value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")


def _validate_fraction_exclusive(name: str, value: float) -> None:
    _validate_number(name, value)
    if not 0.0 < value < 1.0:
        raise ValueError(f"{name} must be greater than 0 and less than 1.")


def _validate_fraction_inclusive(name: str, value: float) -> None:
    _validate_number(name, value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1.")


TAXONOMY_CARD_SCOPE_LAYOUT_PRODUCTION_PARAMS = TaxonomyCardScopeLayoutParams()


def _deterministic_unit_vector(
    *,
    source_node_id: int,
    target_node_id: int,
) -> tuple[float, float, float]:
    angle = (source_node_id * 31 + target_node_id * 17) * _GOLDEN_ANGLE_RADIANS
    return (cos(angle), sin(angle), 1.0)


def _canonical_edges(
    *,
    edges: list[TaxonomyCardScopeLayoutEdge],
    node_ids: set[int],
) -> list[TaxonomyCardScopeLayoutEdge]:
    edge_by_pair: dict[tuple[int, int], TaxonomyCardScopeLayoutEdge] = {}
    for edge in edges:
        if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
            continue
        source_node_id = min(edge.source_node_id, edge.target_node_id)
        target_node_id = max(edge.source_node_id, edge.target_node_id)
        pair = (source_node_id, target_node_id)
        edge_by_pair.setdefault(
            pair,
            TaxonomyCardScopeLayoutEdge(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                strength=edge.strength,
            ),
        )
    return [edge_by_pair[pair] for pair in sorted(edge_by_pair)]


def _world_bounds(nodes: list[TaxonomyCardScopeLayoutNode]) -> TaxonomyCardScopeWorldBounds:
    if not nodes:
        return TaxonomyCardScopeWorldBounds(min_x=0.0, min_y=0.0, max_x=0.0, max_y=0.0)
    return TaxonomyCardScopeWorldBounds(
        min_x=min(node.x for node in nodes),
        min_y=min(node.y for node in nodes),
        max_x=max(node.x for node in nodes),
        max_y=max(node.y for node in nodes),
    )
