"""
Abstract: Shared card-quality criteria for source-pipeline card tasks.
Out of scope: Queue transport behavior and worker protocol instructions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CardQualityCriterion:
    title: str
    description: str


CARD_QUALITY_CRITERIA: tuple[CardQualityCriterion, ...] = (
    CardQualityCriterion(
        title="title_validity",
        description=(
            "The title is unambiguous, precisely scoped, and independently "
            "understandable without requiring additional context."
        ),
    ),
    CardQualityCriterion(
        title="title_content_alignment",
        description=(
            "The title accurately and sufficiently indicates the actual topic "
            "discussed by the content."
        ),
    ),
    CardQualityCriterion(
        title="title_style_validity",
        description=(
            "The title follows <subject> or <subject> (<domain>); <subject> is "
            "preferred by default; the parenthesized domain is used only for "
            "minimal disambiguation; the title uses Title Case with minor "
            "function words such as 'a', 'an', 'the', 'of', and 'in' lowercase "
            "unless they begin the title; full sentences, definition-like "
            "phrases, colon-separated explanatory labels, and unnecessary "
            "qualifiers are invalid."
        ),
    ),
    CardQualityCriterion(
        title="content_coherence",
        description=(
            "The content is self-contained and self-explanatory given standard "
            "domain terminology, without missing context, hidden assumptions, "
            "unresolved references, or implicit external prerequisites that "
            "should be stated."
        ),
    ),
    CardQualityCriterion(
        title="content_atomicity",
        description=(
            "The content represents exactly one indivisible knowledge unit; "
            "content that can be meaningfully split into multiple independent "
            "knowledge units must be split into separate cards when the task "
            "can do so using the provided input."
        ),
    ),
    CardQualityCriterion(
        title="content_latex_validity",
        description=(
            "LaTeX math uses \\( and \\) for inline formulas and \\[ and \\] for "
            "display formulas; $ or $$ delimiters, mismatched delimiters, and malformed "
            "LaTeX syntax are invalid."
        ),
    ),
)

CRITERIA_BY_TITLE = {criterion.title: criterion for criterion in CARD_QUALITY_CRITERIA}


def build_quality_criteria_instruction_text() -> str:
    lines = ["Card quality criteria:"]
    lines.extend(
        f"- {criterion.title}: {criterion.description}" for criterion in CARD_QUALITY_CRITERIA
    )
    return "\n".join(lines)
