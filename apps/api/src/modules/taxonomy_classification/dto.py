"""
Abstract: DTO contracts for taxonomy-classification session and batch orchestration.
Out of scope: Cursor subprocess invocation and database repository wiring.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NodeOutcomeStatus = Literal["assigned", "already_assigned", "error"]
SessionResult = Literal["assigned", "already_assigned"]


class TaxonomyClassificationNodeOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    status: NodeOutcomeStatus
    leaf_id: int | None = Field(default=None, gt=0)
    detail: NonEmptyString | None = None


class TaxonomyClassificationBatchResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    selected_count: int = Field(ge=0)
    assigned_count: int = Field(ge=0)
    unchanged_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    selected_node_ids: list[int] = Field(default_factory=list)
    outcomes: list[TaxonomyClassificationNodeOutcome] = Field(default_factory=list)


class SessionChildrenResponse(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    children: list[TaxonomyNodeRecord] = Field(default_factory=list)


class SessionAssignmentResponse(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    assignment: TaxonomyAssignmentRecord | None = None


class SessionAssignLeafResponse(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    result: SessionResult
    assignment: TaxonomyAssignmentRecord
