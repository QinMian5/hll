"""
Abstract: Unit tests for pure helper behavior in the knowledge-graph repository module.
Out of scope: Database I/O, transaction management, and SQL runtime integration.
"""

from __future__ import annotations

from modules.knowledge_graph.repo import _canonical_edge_pair, _distance_to_similarity


def test_canonical_edge_pair_orders_node_ids() -> None:
    assert _canonical_edge_pair(7, 3) == (3, 7)
    assert _canonical_edge_pair(3, 7) == (3, 7)


def test_distance_to_similarity_clamps_into_unit_interval() -> None:
    assert _distance_to_similarity(-0.5) == 1.0
    assert _distance_to_similarity(0.2) == 0.8
    assert _distance_to_similarity(1.5) == 0.0
