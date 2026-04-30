"""
Abstract: Unit tests for card-review step contracts.
Out of scope: Queue transport behavior and downstream handoff logic.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from source_pipeline.card_review.contracts import ReviewResult, export_card_review_output_schema
from source_pipeline.card_review.instruction import build_card_review_instruction


def test_card_review_schema_is_exported_from_python_contracts() -> None:
    schema = export_card_review_output_schema()

    assert schema["type"] == "object"
    assert set(schema["properties"]) == {"passed", "reason"}
    assert schema["required"] == ["passed"]
    assert "title_validity" not in schema["properties"]


def test_review_result_requires_reason_only_for_failed_reviews() -> None:
    assert ReviewResult(passed=True, reason=None).passed is True
    assert ReviewResult(passed=True, reason="Optional pass explanation.").passed is True
    assert ReviewResult(passed=False, reason="The content has unresolved references.").passed is (
        False
    )

    with pytest.raises(ValidationError):
        ReviewResult(passed=False, reason=None)


def test_card_review_instruction_carries_unified_quality_standard() -> None:
    instruction = build_card_review_instruction()

    assert "Review the provided candidate knowledge card." in instruction
    assert "Evaluate only the provided title and content." in instruction
    assert "Each card represents one knowledge unit." in instruction
    assert "Title Case" in instruction
    assert "<Subject> (<Domain>)" in instruction
    assert "self-contained, and self-explanatory" in instruction
    assert "Definitions, qualifiers, mechanisms, examples, or implications" in instruction
    assert "Do not use external retrieval, memory, or hidden context." in instruction
    assert "Reasons must explain the judgment only" in instruction
    assert "title_validity" not in instruction
