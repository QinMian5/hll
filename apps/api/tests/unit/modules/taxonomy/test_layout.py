"""
Abstract: Unit tests for backend taxonomy card-scope world-coordinate layout.
Out of scope: Redis cache behavior and HTTP response validation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from math import hypot

import pytest

from modules.taxonomy.dto import TaxonomyCardScopeLayoutEdge, TaxonomyCardScopeLayoutNode
from modules.taxonomy.layout import (
    TaxonomyCardScopeLayoutParams,
    build_card_scope_layout,
    slice_card_scope_layout,
)


def _node_position(
    layout_nodes: list[TaxonomyCardScopeLayoutNode],
    node_id: int,
) -> tuple[float, float]:
    for node in layout_nodes:
        if node.id == node_id:
            return (node.x, node.y)
    raise AssertionError(f"Node {node_id} was not in the layout.")


def _distance(
    layout_nodes: list[TaxonomyCardScopeLayoutNode],
    source_node_id: int,
    target_node_id: int,
) -> float:
    source_x, source_y = _node_position(layout_nodes, source_node_id)
    target_x, target_y = _node_position(layout_nodes, target_node_id)
    return hypot(target_x - source_x, target_y - source_y)


def test_build_card_scope_layout_returns_stable_global_coordinates() -> None:
    generated_at = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    nodes = [
        TaxonomyCardScopeLayoutNode(id=12, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=77, scope="outer", x=0.0, y=0.0),
    ]
    edges = [
        TaxonomyCardScopeLayoutEdge(source_node_id=12, target_node_id=77, strength=0.66),
        TaxonomyCardScopeLayoutEdge(source_node_id=12, target_node_id=11, strength=0.91),
    ]

    first = build_card_scope_layout(nodes=nodes, edges=edges, generated_at=generated_at)
    second = build_card_scope_layout(nodes=nodes, edges=edges, generated_at=generated_at)

    assert first == second
    assert first.layout_version == "taxonomy-card-scope-layout-v2"
    assert [node.id for node in first.nodes] == [11, 12, 77]
    assert [(node.id, node.scope) for node in first.nodes] == [
        (11, "inner"),
        (12, "inner"),
        (77, "outer"),
    ]
    assert [(edge.source_node_id, edge.target_node_id) for edge in first.edges] == [
        (11, 12),
        (12, 77),
    ]
    for node in first.nodes:
        assert first.world_bounds.min_x <= node.x <= first.world_bounds.max_x
        assert first.world_bounds.min_y <= node.y <= first.world_bounds.max_y


def test_build_card_scope_layout_uses_edge_strength_in_force_geometry() -> None:
    generated_at = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    nodes = [
        TaxonomyCardScopeLayoutNode(id=10, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=12, scope="outer", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=13, scope="outer", x=0.0, y=0.0),
    ]

    weak_layout = build_card_scope_layout(
        nodes=nodes,
        edges=[TaxonomyCardScopeLayoutEdge(source_node_id=10, target_node_id=11, strength=0.0)],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )
    strong_layout = build_card_scope_layout(
        nodes=nodes,
        edges=[TaxonomyCardScopeLayoutEdge(source_node_id=10, target_node_id=11, strength=1.0)],
        generated_at=generated_at,
    )

    assert _distance(strong_layout.nodes, 10, 11) < _distance(
        weak_layout.nodes,
        10,
        11,
    )


def test_build_card_scope_layout_uses_scaled_seed_radius_for_single_node() -> None:
    layout = build_card_scope_layout(
        nodes=[TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0)],
        edges=[],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )

    assert [(node.x, node.y) for node in layout.nodes] == [(176.0, 0.0)]
    assert layout.world_bounds.model_dump() == {
        "min_x": 176.0,
        "min_y": 0.0,
        "max_x": 176.0,
        "max_y": 0.0,
    }


def test_build_card_scope_layout_accepts_seed_radius_parameters() -> None:
    layout = build_card_scope_layout(
        nodes=[TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0)],
        edges=[],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        params=TaxonomyCardScopeLayoutParams(seed_base_radius=40.0, seed_radius_step=10.0),
    )

    assert [(node.x, node.y) for node in layout.nodes] == [(50.0, 0.0)]
    assert layout.world_bounds.model_dump() == {
        "min_x": 50.0,
        "min_y": 0.0,
        "max_x": 50.0,
        "max_y": 0.0,
    }


def test_taxonomy_card_scope_layout_params_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="alpha_min"):
        TaxonomyCardScopeLayoutParams(alpha_min=1.0)

    with pytest.raises(ValueError, match="simulation_ticks"):
        TaxonomyCardScopeLayoutParams(simulation_ticks=-1)


def test_center_gravity_pulls_each_node_toward_origin() -> None:
    nodes = [
        TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=12, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=13, scope="outer", x=0.0, y=0.0),
    ]
    seeded = build_card_scope_layout(
        nodes=nodes,
        edges=[],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        params=TaxonomyCardScopeLayoutParams(
            seed_base_radius=100.0,
            seed_radius_step=0.0,
            simulation_ticks=0,
        ),
    )

    centered = build_card_scope_layout(
        nodes=nodes,
        edges=[],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        params=TaxonomyCardScopeLayoutParams(
            seed_base_radius=100.0,
            seed_radius_step=0.0,
            simulation_ticks=1,
            velocity_retention=1.0,
            charge_strength=0.0,
            collision_strength=0.0,
            center_gravity_strength=0.4,
        ),
    )

    for node in nodes:
        assert hypot(*_node_position(centered.nodes, node.id)) < hypot(
            *_node_position(seeded.nodes, node.id),
        )


def test_radial_boundary_pulls_nodes_inside_soft_circle() -> None:
    nodes = [
        TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=12, scope="inner", x=0.0, y=0.0),
        TaxonomyCardScopeLayoutNode(id=13, scope="outer", x=0.0, y=0.0),
    ]
    seeded = build_card_scope_layout(
        nodes=nodes,
        edges=[],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        params=TaxonomyCardScopeLayoutParams(
            seed_base_radius=120.0,
            seed_radius_step=0.0,
            simulation_ticks=0,
        ),
    )

    bounded = build_card_scope_layout(
        nodes=nodes,
        edges=[],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        params=TaxonomyCardScopeLayoutParams(
            seed_base_radius=120.0,
            seed_radius_step=0.0,
            simulation_ticks=1,
            velocity_retention=1.0,
            charge_strength=0.0,
            collision_strength=0.0,
            center_gravity_strength=0.0,
            radial_boundary_radius=50.0,
            radial_boundary_strength=0.6,
        ),
    )

    for node in nodes:
        assert hypot(*_node_position(bounded.nodes, node.id)) < hypot(
            *_node_position(seeded.nodes, node.id),
        )


def test_slice_card_scope_layout_returns_only_nodes_and_edges_inside_bounds() -> None:
    layout = build_card_scope_layout(
        nodes=[
            TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0),
            TaxonomyCardScopeLayoutNode(id=12, scope="inner", x=0.0, y=0.0),
            TaxonomyCardScopeLayoutNode(id=77, scope="outer", x=0.0, y=0.0),
        ],
        edges=[
            TaxonomyCardScopeLayoutEdge(source_node_id=11, target_node_id=12, strength=0.91),
            TaxonomyCardScopeLayoutEdge(source_node_id=12, target_node_id=77, strength=0.66),
        ],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )
    first_node = layout.nodes[0]

    sliced = slice_card_scope_layout(
        layout,
        min_x=first_node.x - 1.0,
        min_y=first_node.y - 1.0,
        max_x=first_node.x + 1.0,
        max_y=first_node.y + 1.0,
    )

    assert [node.id for node in sliced.nodes] == [first_node.id]
    assert sliced.edges == []
    assert sliced.requested_bounds.model_dump() == {
        "min_x": first_node.x - 1.0,
        "min_y": first_node.y - 1.0,
        "max_x": first_node.x + 1.0,
        "max_y": first_node.y + 1.0,
    }


def test_build_card_scope_layout_handles_empty_scope() -> None:
    layout = build_card_scope_layout(
        nodes=[],
        edges=[],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )

    assert layout.node_count == 0
    assert layout.edge_count == 0
    assert layout.world_bounds.model_dump() == {
        "min_x": 0.0,
        "min_y": 0.0,
        "max_x": 0.0,
        "max_y": 0.0,
    }
