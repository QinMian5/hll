"""
Abstract: Pydantic contracts for the card-repair step.
Out of scope: Queue transport behavior and repair-result orchestration.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter

from source_pipeline.card_review.contracts import ReviewResult
from source_pipeline.page_to_card.contracts import CardDraft


class CardRepairInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card: CardDraft
    review: ReviewResult


class CardRepairResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cards: list[CardDraft]


CARD_REPAIR_RESULT_ADAPTER = TypeAdapter(CardRepairResult)


def export_card_repair_output_schema() -> dict[str, Any]:
    return CARD_REPAIR_RESULT_ADAPTER.json_schema()
