"""
Abstract: Unit tests for pure helper behavior in the knowledge-graph repository module.
Out of scope: Database I/O, transaction management, and SQL runtime integration.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from modules.knowledge_graph.dto import ProjectionEdge
from modules.knowledge_graph.repo import _canonical_edge_pair, _dot_product_to_similarity


def test_canonical_edge_pair_orders_node_ids() -> None:
    assert _canonical_edge_pair(7, 3) == (3, 7)
    assert _canonical_edge_pair(3, 7) == (3, 7)


def test_dot_product_to_similarity_clamps_into_unit_interval() -> None:
    assert _dot_product_to_similarity(-1.5) == 0.0
    assert _dot_product_to_similarity(-1.0) == 0.0
    assert _dot_product_to_similarity(0.0) == 0.5
    assert _dot_product_to_similarity(0.6) == 0.8
    assert _dot_product_to_similarity(1.0) == 1.0
    assert _dot_product_to_similarity(1.5) == 1.0


def test_projection_edge_requires_canonical_node_order() -> None:
    with pytest.raises(ValidationError):
        ProjectionEdge(node_a_id=7, node_b_id=3, strength=0.8)
