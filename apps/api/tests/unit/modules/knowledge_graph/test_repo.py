"""
Abstract: Unit tests for pure helper behavior in the knowledge-graph repository module.
Out of scope: Database I/O, transaction management, and SQL runtime integration.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from modules.knowledge_graph.dto import ProjectionEdge
from modules.knowledge_graph.repo import (
    _canonical_edge_pair,
    _dot_product_to_similarity,
    _normalize_search_text,
    _title_match_boost,
)


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


def test_normalize_search_text_collapses_case_and_spacing() -> None:
    assert _normalize_search_text("  Quantum   Mechanics  ") == "quantum mechanics"


def test_title_match_boost_orders_exact_phrase_tokens_and_content_only() -> None:
    exact_title = _title_match_boost(title="Quantum Mechanics", query_text="quantum mechanics")
    phrase_title = _title_match_boost(
        title="Introduction to Quantum Mechanics",
        query_text="quantum mechanics",
    )
    all_tokens_title = _title_match_boost(
        title="Mechanics and Quantum Notes",
        query_text="quantum mechanics",
    )
    content_only = _title_match_boost(title="Physics Notes", query_text="quantum mechanics")

    assert exact_title > phrase_title > all_tokens_title > content_only


def test_projection_edge_requires_canonical_node_order() -> None:
    with pytest.raises(ValidationError):
        ProjectionEdge(node_a_id=7, node_b_id=3, strength=0.8)
