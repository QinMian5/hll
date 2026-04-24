"""
Abstract: Build the task-specific worker instruction for candidate-card repair.
Out of scope: Output-schema generation and queue submission mechanics.
"""

from __future__ import annotations

from source_pipeline.card_review.criteria import build_quality_criteria_instruction_text


def build_card_repair_instruction() -> str:
    return f"""
Repair the provided candidate knowledge card.

Work only from the provided payload.
The payload contains:
- card: the rejected candidate card with title and content
- review: the accepted review result for that card

Use the failed review dimensions and their reasons to repair the card.
If the card can be repaired, produce one or more corrected atomic card drafts.
If the card cannot be repaired from the provided card and review result, produce no cards.

{build_quality_criteria_instruction_text()}

Do not use external retrieval, memory, or hidden context.
Do not invent claims that are not supported by the rejected card content.
""".strip()


__all__ = ["build_card_repair_instruction"]
