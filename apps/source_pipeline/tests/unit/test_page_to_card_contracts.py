"""
Abstract: Unit tests for page-to-card step contracts.
Out of scope: Queue transport behavior and runtime orchestration logic.
"""

from __future__ import annotations

from source_pipeline.page_to_card.contracts import export_page_to_card_output_schema


def test_page_to_card_schema_is_exported_from_python_contracts() -> None:
    schema = export_page_to_card_output_schema()

    assert schema["type"] == "array"
    assert schema["items"]["$ref"] == "#/$defs/CardDraft"
    assert schema["$defs"]["CardDraft"]["required"] == ["title", "content"]
