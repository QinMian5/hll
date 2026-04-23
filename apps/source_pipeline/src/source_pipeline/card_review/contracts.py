"""
Abstract: Pydantic contracts for the card-review step.
Out of scope: Queue transport behavior and review-result consumption policy.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    reason: str | None = Field(
        default=None,
        description=("Why this review dimension failed. Null is allowed only when passed is true."),
    )

    @model_validator(mode="after")
    def validate_reason(self) -> ReviewItem:
        if self.passed:
            return self
        if self.reason is None:
            raise ValueError("reason must be present when passed is false")
        return self


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_validity: ReviewItem = Field(
        description=(
            "Whether the title is unambiguous, precisely scoped, and independently "
            "understandable without requiring additional context."
        ),
    )
    title_content_alignment: ReviewItem = Field(
        description=(
            "Whether the title accurately and sufficiently indicates the actual topic "
            "of the content."
        ),
    )
    title_style_validity: ReviewItem = Field(
        description=(
            "Whether the title follows the required naming style. A valid title must "
            "use one of these patterns: <subject> or <subject> (<domain>). Prefer "
            "<subject> by default. Use the parenthesized <domain> only when minimal "
            "disambiguation is genuinely necessary. The title must use Title Case, "
            "capitalizing principal words while keeping minor function words such as "
            "'a', 'an', 'the', 'of', and 'in' lowercase unless they begin the title. "
            "Reject full sentences, definition-like phrases, colon-separated "
            "explanatory labels, and unnecessary qualifiers."
        ),
    )
    content_coherence: ReviewItem = Field(
        description=(
            "Whether the content is self-contained and self-explanatory given standard "
            "domain terminology. Reject content that depends on missing context, "
            "hidden assumptions, unresolved references, or implicit external "
            "prerequisites that should have been stated."
        ),
    )
    content_atomicity: ReviewItem = Field(
        description=(
            "Whether the content represents exactly one indivisible knowledge unit. "
            "Reject content that can be meaningfully decomposed into multiple smaller "
            "independent knowledge units, even if they are related."
        ),
    )
    content_latex_validity: ReviewItem = Field(
        description=(
            "Whether LaTeX expressions in the content, if any, use standard and "
            "syntactically correct math delimiters and notation. Inline math must use "
            "\\( and \\), and display math must use \\[ and \\]. Reject $ or $$ "
            "delimiters, mismatched delimiters, and malformed LaTeX syntax."
        ),
    )


def export_card_review_output_schema() -> dict[str, Any]:
    return ReviewResult.model_json_schema()
