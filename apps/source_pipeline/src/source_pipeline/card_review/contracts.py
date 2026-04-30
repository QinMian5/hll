"""
Abstract: Pydantic contracts for the card-review step.
Out of scope: Queue transport behavior and review-result consumption policy.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool = Field(
        description="Whether the card satisfies the card quality standard.",
    )
    reason: str | None = Field(
        default=None,
        description="Why the card failed the card quality standard. Required when passed is false.",
    )

    @model_validator(mode="after")
    def validate_reason(self) -> ReviewResult:
        if self.passed:
            return self
        if self.reason is None or not self.reason.strip():
            raise ValueError("reason must be present when passed is false")
        return self


def export_card_review_output_schema() -> dict[str, Any]:
    return ReviewResult.model_json_schema()
