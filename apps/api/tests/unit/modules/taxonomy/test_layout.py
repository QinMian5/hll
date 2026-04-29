"""
Abstract: Unit tests for backend taxonomy leaf world-coordinate layout.
Out of scope: Redis cache behavior and HTTP response validation.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from modules.taxonomy.dto import TaxonomyLeafLayoutEdge, TaxonomyLeafLayoutNode
from modules.taxonomy.layout import build_leaf_layout, slice_leaf_layout


def test_build_leaf_layout_returns_stable_global_coordinates() -> None:
    generated_at = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    nodes = [
        TaxonomyLeafLayoutNode(id=12, scope="inner", x=0.0, y=0.0),
        TaxonomyLeafLayoutNode(id=11, scope="inner", x=0.0, y=0.0),
        TaxonomyLeafLayoutNode(id=77, scope="outer", x=0.0, y=0.0),
    ]
    edges = [
        TaxonomyLeafLayoutEdge(source_node_id=12, target_node_id=77, strength=0.66),
        TaxonomyLeafLayoutEdge(source_node_id=12, target_node_id=11, strength=0.91),
    ]

    first = build_leaf_layout(nodes=nodes, edges=edges, generated_at=generated_at)
    second = build_leaf_layout(nodes=nodes, edges=edges, generated_at=generated_at)

    assert first == second
    assert [node.id for node in first.nodes] == [11, 12, 77]
    assert [(node.id, node.scope) for node in first.nodes] == [
        (11, "inner"),
        (12, "inner"),
        (77, "outer"),
    ]
    assert first.nodes[0].x == pytest.approx(100.0)
    assert first.nodes[0].y == pytest.approx(0.0)
    assert [(edge.source_node_id, edge.target_node_id) for edge in first.edges] == [
        (11, 12),
        (12, 77),
    ]


def test_slice_leaf_layout_returns_only_nodes_and_edges_inside_bounds() -> None:
    layout = build_leaf_layout(
        nodes=[
            TaxonomyLeafLayoutNode(id=11, scope="inner", x=0.0, y=0.0),
            TaxonomyLeafLayoutNode(id=12, scope="inner", x=0.0, y=0.0),
            TaxonomyLeafLayoutNode(id=77, scope="outer", x=0.0, y=0.0),
        ],
        edges=[
            TaxonomyLeafLayoutEdge(source_node_id=11, target_node_id=12, strength=0.91),
            TaxonomyLeafLayoutEdge(source_node_id=12, target_node_id=77, strength=0.66),
        ],
        generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )

    sliced = slice_leaf_layout(
        layout,
        min_x=-120.0,
        min_y=-20.0,
        max_x=120.0,
        max_y=20.0,
    )

    assert [node.id for node in sliced.nodes] == [11]
    assert sliced.edges == []
    assert sliced.requested_bounds.model_dump() == {
        "min_x": -120.0,
        "min_y": -20.0,
        "max_x": 120.0,
        "max_y": 20.0,
    }


def test_build_leaf_layout_handles_empty_leaf() -> None:
    layout = build_leaf_layout(
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
