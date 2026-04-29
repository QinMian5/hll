"""
Abstract: Unit tests for card-repair step contracts and task instruction.
Out of scope: Queue transport behavior and runtime repair orchestration.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from source_pipeline.card_repair.contracts import (
    CardRepairInput,
    CardRepairResult,
    export_card_repair_output_schema,
)
from source_pipeline.card_repair.instruction import build_card_repair_instruction
from source_pipeline.card_review.contracts import ReviewItem, ReviewResult
from source_pipeline.card_review.criteria import CARD_QUALITY_CRITERIA
from source_pipeline.page_to_card.contracts import CardDraft


def _passing_review() -> ReviewResult:
    item = ReviewItem(passed=True)
    return ReviewResult(
        title_validity=item,
        title_content_alignment=item,
        title_style_validity=item,
        content_coherence=item,
        content_atomicity=item,
        content_latex_validity=item,
    )


def test_card_repair_input_accepts_rejected_card_and_review_result() -> None:
    repair_input = CardRepairInput(
        card=CardDraft(title="Quantum State", content="A quantum state describes a system."),
        review=_passing_review(),
    )

    assert repair_input.card.title == "Quantum State"
    assert repair_input.review.content_atomicity.passed is True


def test_card_repair_input_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CardRepairInput(
            card=CardDraft(title="Quantum State", content="A quantum state describes a system."),
            review=_passing_review(),
            unexpected=True,
        )


def test_card_repair_result_accepts_cards_list() -> None:
    result = CardRepairResult(
        cards=[
            CardDraft(title="Quantum State", content="A quantum state describes a system."),
        ],
    )

    assert result.cards[0].title == "Quantum State"


def test_card_repair_schema_exports_only_cards_result_contract() -> None:
    schema = export_card_repair_output_schema()

    assert schema["type"] == "object"
    assert schema["required"] == ["cards"]
    assert set(schema["properties"]) == {"cards"}
    assert schema["properties"]["cards"]["items"]["$ref"] == "#/$defs/CardDraft"


def test_card_repair_instruction_includes_shared_quality_dimensions_without_protocol_noise() -> (
    None
):
    instruction = build_card_repair_instruction()

    assert "Repair the provided candidate knowledge card." in instruction
    assert "Work only from the provided payload." in instruction
    assert "focused, compact, and context-sufficient" in instruction
    assert "Choose the appropriate granularity" in instruction
    assert "Do not optimize for the shortest possible statement." in instruction
    assert "Do not use external retrieval, memory, or hidden context." in instruction
    assert "Return ONLY a JSON object" not in instruction
    for criterion in CARD_QUALITY_CRITERIA:
        assert criterion.title in instruction
