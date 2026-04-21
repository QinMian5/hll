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
        description=(
            "Why this review dimension failed. Null is allowed only when passed is true."
        ),
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

    title_validity: ReviewItem
    title_content_alignment: ReviewItem
    title_style_validity: ReviewItem
    content_coherence: ReviewItem
    content_atomicity: ReviewItem
    content_latex_validity: ReviewItem


def export_card_review_output_schema() -> dict[str, Any]:
    return ReviewResult.model_json_schema()
