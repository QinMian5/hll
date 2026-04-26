"""
Abstract: Pydantic contracts for taxonomy-classification job payloads and results.
Out of scope: Queue transport behavior and taxonomy assignment persistence.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator


class TaxonomyClassificationNodeRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: PositiveInt
    name: str = Field(min_length=1)


class TaxonomyClassificationCardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: PositiveInt
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class TaxonomyClassificationJobPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope_node: TaxonomyClassificationNodeRef
    source_unclassified_node: TaxonomyClassificationNodeRef
    card: TaxonomyClassificationCardPayload
    children: list[TaxonomyClassificationNodeRef]
    allow_unclassified: bool = True


class TaxonomyClassificationTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["child", "unclassified"]
    reason: str = Field(min_length=1)
    child_id: PositiveInt | None = None

    @model_validator(mode="after")
    def validate_target_shape(self) -> TaxonomyClassificationTarget:
        if self.kind == "child" and self.child_id is None:
            raise ValueError("child targets require child_id")
        if self.kind == "unclassified" and self.child_id is not None:
            raise ValueError("unclassified targets must not include child_id")
        return self


class TaxonomyClassificationAcceptedResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: TaxonomyClassificationTarget


def export_taxonomy_classification_output_schema() -> dict[str, object]:
    return TaxonomyClassificationAcceptedResult.model_json_schema()


__all__ = [
    "TaxonomyClassificationAcceptedResult",
    "TaxonomyClassificationCardPayload",
    "TaxonomyClassificationJobPayload",
    "TaxonomyClassificationNodeRef",
    "TaxonomyClassificationTarget",
    "export_taxonomy_classification_output_schema",
]
