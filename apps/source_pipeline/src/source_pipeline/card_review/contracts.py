"""
Abstract: Pydantic contracts for the card-review step.
Out of scope: Queue transport behavior and review-result consumption policy.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from source_pipeline.card_review.criteria import CRITERIA_BY_TITLE


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
        description=CRITERIA_BY_TITLE["title_validity"].description,
    )
    title_content_alignment: ReviewItem = Field(
        description=CRITERIA_BY_TITLE["title_content_alignment"].description,
    )
    title_style_validity: ReviewItem = Field(
        description=CRITERIA_BY_TITLE["title_style_validity"].description,
    )
    content_coherence: ReviewItem = Field(
        description=CRITERIA_BY_TITLE["content_coherence"].description,
    )
    content_atomicity: ReviewItem = Field(
        description=CRITERIA_BY_TITLE["content_atomicity"].description,
    )
    content_latex_validity: ReviewItem = Field(
        description=CRITERIA_BY_TITLE["content_latex_validity"].description,
    )


def export_card_review_output_schema() -> dict[str, Any]:
    return ReviewResult.model_json_schema()
