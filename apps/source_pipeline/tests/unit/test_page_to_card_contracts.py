"""
Abstract: Unit tests for page-to-card step contracts.
Out of scope: Queue transport behavior and runtime orchestration logic.
"""

from __future__ import annotations

from source_pipeline.card_review.criteria import CARD_QUALITY_STANDARD
from source_pipeline.page_to_card.contracts import export_page_to_card_output_schema
from source_pipeline.page_to_card.instruction import build_page_to_card_instruction


def test_page_to_card_schema_is_exported_from_python_contracts() -> None:
    schema = export_page_to_card_output_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["cards"]
    assert schema["properties"]["cards"]["type"] == "array"
    assert schema["properties"]["cards"]["items"]["$ref"] == "#/$defs/CardDraft"
    assert schema["$defs"]["CardDraft"]["required"] == ["title", "content"]


def test_page_to_card_instruction_encodes_task_guidance_without_protocol_noise() -> None:
    instruction = build_page_to_card_instruction()

    assert "independent knowledge units" in instruction
    assert "focused, compact, and context-sufficient" in instruction
    assert "Do not optimize for the shortest possible statement." in instruction
    assert "Title Case" in instruction
    assert "<Subject> (<Domain>)" in instruction
    assert "Do not invent claims" in instruction
    assert "If no worthwhile knowledge units are present, return no cards." in instruction
    assert "about 10" not in instruction
    assert "Return ONLY a JSON object" not in instruction
    assert "title_validity" not in instruction


def test_page_to_card_instruction_uses_shared_quality_standard() -> None:
    instruction = build_page_to_card_instruction()

    assert CARD_QUALITY_STANDARD in instruction
