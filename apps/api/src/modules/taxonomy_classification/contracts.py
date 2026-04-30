"""
Abstract: Pydantic contracts for taxonomy-classification job payloads and results.
Out of scope: Queue transport behavior and taxonomy assignment persistence.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TaxonomyClassificationChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: NonEmptyString


class TaxonomyClassificationCardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyString
    content: NonEmptyString


class TaxonomyClassificationJobPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope_path: NonEmptyString
    card: TaxonomyClassificationCardPayload
    children: list[TaxonomyClassificationChildPayload]


class TaxonomyClassificationAcceptedResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_name: NonEmptyString


def export_taxonomy_classification_output_schema() -> dict[str, object]:
    return TaxonomyClassificationAcceptedResult.model_json_schema()


__all__ = [
    "TaxonomyClassificationAcceptedResult",
    "TaxonomyClassificationCardPayload",
    "TaxonomyClassificationChildPayload",
    "TaxonomyClassificationJobPayload",
    "export_taxonomy_classification_output_schema",
]
