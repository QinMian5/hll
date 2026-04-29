"""
Abstract: Unit tests for taxonomy-classification worker instruction text.
Out of scope: Queue transport and result persistence.
"""

from __future__ import annotations

import pytest

from modules.taxonomy_classification.instruction import build_taxonomy_classification_instruction


@pytest.mark.unit
def test_instruction_disallows_parent_or_unlisted_category_selection() -> None:
    instruction = build_taxonomy_classification_instruction()

    assert "Do not choose a parent" in instruction
    assert "ancestor" in instruction
    assert "new category" in instruction
    assert "not listed" in instruction
