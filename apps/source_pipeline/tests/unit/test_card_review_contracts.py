"""
Abstract: Unit tests for card-review step contracts.
Out of scope: Queue transport behavior and downstream handoff logic.
"""

from __future__ import annotations

from source_pipeline.card_review.contracts import export_card_review_output_schema


def test_card_review_schema_is_exported_from_python_contracts() -> None:
    schema = export_card_review_output_schema()

    assert schema["type"] == "object"
    assert "title_validity" in schema["properties"]
    assert "passed" not in schema["properties"]

