"""
Abstract: Pydantic DTOs used by the knowledge-graph domain service and ports.
Out of scope: SQLAlchemy persistence mapping and HTTP request/response contracts.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class KnowledgeCardMatch(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    title: NonEmptyString
    content: NonEmptyString


class ConnectedTitleCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    title: NonEmptyString


class SimilarNodeCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    similarity: float = Field(ge=0.0, le=1.0)


class ProjectionCardNode(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    title: NonEmptyString
    content: NonEmptyString


class ProjectionEdge(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_a_id: int = Field(gt=0)
    node_b_id: int = Field(gt=0)
    strength: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_canonical_pair(self) -> ProjectionEdge:
        if self.node_a_id >= self.node_b_id:
            raise ValueError("node_a_id must be smaller than node_b_id.")
        return self


class TaxonomyClassificationNodeInput(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    title: NonEmptyString
    content: NonEmptyString
