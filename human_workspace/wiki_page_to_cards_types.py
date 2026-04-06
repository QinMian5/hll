"""
Abstract: Typed page-level contracts for external page-to-card orchestration.
Out of scope: Cursor execution, CLI invocation, and processed-document updates.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    create_model,
    model_validator,
)


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class PageRecord(StrictModel):
    page_id: int = Field(description="Stable Wikipedia page identifier.")
    url: NonEmptyText = Field(description="Canonical source URL for the page.")
    title: NonEmptyText = Field(description="Human-readable page title.")
    clean_text: NonEmptyText = Field(
        description="Normalized page text supplied to the page-card orchestrator."
    )


class PageResult(StrictModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "description": (
                "Final page-level result for one page-agent session. "
                "Return exactly one JSON object in this shape after the page session finishes."
            )
        },
    )

    page_id: int = Field(description="Stable Wikipedia page identifier.")
    completed: bool = Field(
        description=(
            "Final page-level success flag for one page-agent session. "
            "Set this field to true only when the page session has finished successfully and every card "
            "the agent chose to keep has already been accepted by the reviewed write-card command. "
            "Set this field to false when the page session cannot be completed."
        )
    )
    reason: NonEmptyText | None = Field(
        default=None,
        description=(
            "Concise failure reason for the page-level attempt. "
            "This field must be null when completed is true and must be a non-empty failure reason when completed is false."
        ),
    )

    @model_validator(mode="after")
    def validate_reason_contract(self) -> "PageResult":
        if self.completed and self.reason is not None:
            raise ValueError("completed page results must not include a reason")
        if not self.completed and self.reason is None:
            raise ValueError("failed page results must include a non-empty reason")
        return self


def completed_page_result(page_id: int) -> PageResult:
    return PageResult(page_id=page_id, completed=True, reason=None)


def failed_page_result(page_id: int, reason: str) -> PageResult:
    return PageResult(page_id=page_id, completed=False, reason=reason)


def build_page_result_adapter(page_id: int) -> TypeAdapter:
    page_id_description = (
        f"Stable Wikipedia page identifier for this page session. The value must be exactly {page_id}."
    )
    page_result_model = create_model(
        f"PageResultForPage{page_id}",
        __base__=PageResult,
        page_id=(Literal[page_id], Field(description=page_id_description)),
    )
    return TypeAdapter(page_result_model)


def parse_page_result_payload(page_id: int, payload: str) -> PageResult:
    text = payload.strip()
    if not text:
        raise ValueError("page agent returned empty result text")

    return build_page_result_adapter(page_id).validate_json(text)
