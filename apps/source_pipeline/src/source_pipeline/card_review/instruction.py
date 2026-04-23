"""
Abstract: Build the task-specific worker instruction for candidate-card review.
Out of scope: Review-schema generation and queue submission mechanics.
"""

from __future__ import annotations


def build_card_review_instruction() -> str:
    return """
Review the provided candidate knowledge card.

Work only from the provided payload.
The payload contains one candidate card with:
- title
- content

Evaluate only the provided title and content.
Do not use external retrieval, memory, or hidden context.
Reasons must explain the judgment only and must not provide rewrite advice.
""".strip()


__all__ = ["build_card_review_instruction"]
