"""
Abstract: Build the task-specific worker instruction for candidate-card review.
Out of scope: Review-schema generation and queue submission mechanics.
"""

from __future__ import annotations

from source_pipeline.card_review.criteria import build_quality_criteria_instruction_text


def build_card_review_instruction() -> str:
    return f"""
Review the provided candidate knowledge card.

Work only from the provided payload.
The payload contains one candidate card with:
- title
- content

Evaluate only the provided title and content.
Return a single overall judgment for whether the card satisfies the card quality standard.

{build_quality_criteria_instruction_text()}

Do not use external retrieval, memory, or hidden context.
Reasons must explain the judgment only and must not provide rewrite advice.
""".strip()


__all__ = ["build_card_review_instruction"]
