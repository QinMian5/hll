"""
Abstract: Unit tests for card-review step contracts.
Out of scope: Queue transport behavior and downstream handoff logic.
"""

from __future__ import annotations

from source_pipeline.card_review.contracts import export_card_review_output_schema
from source_pipeline.card_review.instruction import build_card_review_instruction


def test_card_review_schema_is_exported_from_python_contracts() -> None:
    schema = export_card_review_output_schema()

    assert schema["type"] == "object"
    assert "title_validity" in schema["properties"]
    assert "passed" not in schema["properties"]


def test_card_review_schema_carries_review_semantics_in_field_descriptions() -> None:
    schema = export_card_review_output_schema()

    assert "unambiguous" in schema["properties"]["title_validity"]["description"]
    assert "Title Case" in schema["properties"]["title_style_validity"]["description"]
    assert (
        "meaningful context or explanation beyond the title"
        in schema["properties"]["content_coherence"]["description"]
    )
    assert (
        "not the smallest possible fact fragment"
        in schema["properties"]["content_atomicity"]["description"]
    )
    assert "$ or $$" in schema["properties"]["content_latex_validity"]["description"]


def test_card_review_instruction_stays_minimal_when_schema_carries_dimension_details() -> None:
    instruction = build_card_review_instruction()

    assert "Review the provided candidate knowledge card." in instruction
    assert "Evaluate only the provided title and content." in instruction
    assert "Do not use external retrieval, memory, or hidden context." in instruction
    assert "Reasons must explain the judgment only" in instruction
    assert "title_validity" not in instruction
