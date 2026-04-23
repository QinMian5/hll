"""
Abstract: Build the task-specific worker instruction for page-to-card extraction.
Out of scope: Output-schema generation and queue submission mechanics.
"""

from __future__ import annotations


def build_page_to_card_instruction() -> str:
    return """
Extract atomic knowledge cards from the provided source unit.

Work only from the provided payload.
The payload represents one source unit and includes the source title,
source content, and source metadata.

Your task is to identify the independent atomic knowledge units in this
source unit and express them as knowledge cards.

A knowledge card has exactly two semantic fields:
- title: the precise name of the knowledge unit
- content: a self-contained explanation of exactly that one knowledge unit

Requirements for every extracted card:
- The title must be unambiguous, precisely scoped, and independently
  understandable without additional context.
- The title must follow one of these patterns: <subject> or <subject> (<domain>).
- Prefer <subject> by default.
- Use the parenthesized <domain> only when minimal disambiguation is genuinely necessary.
- The title must use Title Case, capitalizing principal words while
  keeping minor function words such as 'a', 'an', 'the', 'of', and
  'in' lowercase unless they begin the title.
- The content must be self-contained and self-explanatory given standard domain terminology.
- The content must represent exactly one indivisible knowledge unit.
- Do not merge multiple independent knowledge units into one card.
- Do not produce duplicate or near-duplicate cards.
- Do not invent claims that are not supported by the provided source unit.
- If LaTeX math appears in content, inline math must use \\( and \\),
  and display math must use \\[ and \\]. Do not use $ or $$ delimiters.

Extraction policy:
- Extract the worthwhile independent atomic knowledge units supported by
  the provided source unit.
- Prioritize foundational and reusable knowledge units over incidental
  details, boilerplate, navigation text, or editorial noise.
- If no worthwhile atomic knowledge units are present, return no cards.
""".strip()


__all__ = ["build_page_to_card_instruction"]
