"""
Abstract: Unit tests for taxonomy-classification worker instruction text.
Out of scope: Queue transport and result persistence.
"""

from __future__ import annotations

import pytest

from modules.taxonomy_classification.instruction import build_taxonomy_classification_instruction


@pytest.mark.unit
def test_instruction_uses_minimal_task_guidance() -> None:
    instruction = build_taxonomy_classification_instruction()

    assert instruction == (
        "Classify the supplied card within the supplied taxonomy scope path into exactly "
        "one supplied direct child taxonomy category, or keep it in Unclassified when none "
        "of the children fit."
    )
    assert "target_name" not in instruction
    assert "case-insensitive" not in instruction
    assert "child_id" not in instruction
    assert "reason" not in instruction
