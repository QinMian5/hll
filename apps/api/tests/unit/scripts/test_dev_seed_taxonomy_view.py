"""
Abstract: Unit tests for development taxonomy-view seed blueprint and guards.
Out of scope: Database writes and GraphView rendering behavior.
"""

from __future__ import annotations

import pytest

from entrypoints.ops.dev_seed_taxonomy_view import (
    DEV_SEED_BRANCHES,
    DEV_SEED_CARD_SPECS,
    DEV_SEED_EDGE_SPECS,
    assert_development_database_url,
)


@pytest.mark.unit
def test_seed_blueprint_uses_placeholder_taxonomy_cards_and_hardcoded_edges() -> None:
    assert DEV_SEED_BRANCHES == {
        "Branch1": ("Leaf1", "Leaf2"),
        "Branch2": ("Leaf3", "Leaf4"),
    }
    assert [card.title for card in DEV_SEED_CARD_SPECS] == [
        "Card1",
        "Card2",
        "Card3",
        "Card4",
        "Card5",
        "Card6",
        "Card7",
        "Card8",
    ]
    assert {card.leaf_name for card in DEV_SEED_CARD_SPECS} == {
        "Leaf1",
        "Leaf2",
        "Leaf3",
        "Leaf4",
    }
    assert [(edge.left_title, edge.right_title) for edge in DEV_SEED_EDGE_SPECS] == [
        ("Card1", "Card2"),
        ("Card2", "Card3"),
        ("Card3", "Card4"),
        ("Card4", "Card5"),
        ("Card5", "Card6"),
        ("Card6", "Card7"),
        ("Card7", "Card8"),
        ("Card1", "Card8"),
        ("Card2", "Card6"),
    ]


@pytest.mark.unit
def test_dev_seed_rejects_non_development_database_urls() -> None:
    with pytest.raises(ValueError, match="development database"):
        assert_development_database_url(
            "postgresql+psycopg://knowledge_app:secret@prod-db:5432/knowledge"
        )


@pytest.mark.unit
def test_dev_seed_accepts_local_and_compose_development_database_urls() -> None:
    assert_development_database_url(
        "postgresql+psycopg://knowledge_app:secret@127.0.0.1:5432/knowledge"
    )
    assert_development_database_url(
        "postgresql+psycopg://knowledge_app:secret@localhost:5432/knowledge"
    )
