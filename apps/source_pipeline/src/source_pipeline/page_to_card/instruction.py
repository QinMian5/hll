"""
Abstract: Build the task-specific worker instruction for page-to-card extraction.
Out of scope: Output-schema generation and queue submission mechanics.
"""

from __future__ import annotations

from source_pipeline.card_review.criteria import build_quality_criteria_instruction_text


def build_page_to_card_instruction() -> str:
    return f"""
Extract focused, compact, and context-sufficient knowledge cards from the
provided source unit.

Work only from the provided payload.
The payload represents one source unit and includes the source title,
source content, and source metadata.

Your task is to identify the independent atomic knowledge units in this
source unit and express them as knowledge cards.

A knowledge card has exactly two semantic fields:
- title: the precise name of the knowledge unit
- content: a compact, context-sufficient explanation of exactly that one
  knowledge unit

{build_quality_criteria_instruction_text()}

Additional extraction requirements:
- Do not merge multiple independent knowledge units into one card.
- Preserve the essential qualifiers and explanatory context needed to
  understand each selected unit outside the original source.
- Do not optimize for the shortest possible statement.
- Do not produce duplicate or near-duplicate cards.
- Do not invent claims that are not supported by the provided source unit.

Extraction policy:
- Extract the worthwhile independent atomic knowledge units supported by
  the provided source unit.
- Prioritize foundational and reusable knowledge units over incidental
  details, boilerplate, navigation text, or editorial noise.
- If no worthwhile atomic knowledge units are present, return no cards.
""".strip()


__all__ = ["build_page_to_card_instruction"]
