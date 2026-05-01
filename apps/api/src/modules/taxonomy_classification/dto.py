"""
Abstract: DTO contracts for taxonomy-classification session and batch orchestration.
Out of scope: Cursor subprocess invocation and database repository wiring.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NodeOutcomeStatus = Literal["assigned", "already_assigned", "error"]
SessionResult = Literal["assigned", "already_assigned"]
SubmissionSelectionKind = Literal["scope_name", "scope_path", "all_unclassified"]


class TaxonomyClassificationSubmissionSelection(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    kind: SubmissionSelectionKind
    scope_name: NonEmptyString | None = None
    scope_path: tuple[NonEmptyString, ...] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_selection_shape(self) -> TaxonomyClassificationSubmissionSelection:
        if self.kind == "scope_name" and (self.scope_name is None or self.scope_path is not None):
            raise ValueError("scope_name selection requires only scope_name")
        if self.kind == "scope_path" and (self.scope_path is None or self.scope_name is not None):
            raise ValueError("scope_path selection requires only scope_path")
        if self.kind == "all_unclassified" and (
            self.scope_name is not None or self.scope_path is not None
        ):
            raise ValueError("all_unclassified selection does not accept a scope")
        return self


class TaxonomyClassificationScopeSummary(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    scope_node_id: int = Field(gt=0)
    breadcrumb: tuple[NonEmptyString, ...] = Field(min_length=1)
    regular_child_count: int = Field(ge=0)
    submitted_count: int = Field(ge=0)
    reused_idempotent_count: int = Field(ge=0)
    already_linked_count: int = Field(ge=0)
    skipped_no_children: bool = False


class TaxonomyClassificationSubmissionResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    selected_scope_count: int = Field(ge=0)
    submitted_count: int = Field(ge=0)
    reused_idempotent_count: int = Field(ge=0)
    already_linked_count: int = Field(ge=0)
    skipped_no_children: int = Field(ge=0)
    scopes: list[TaxonomyClassificationScopeSummary] = Field(default_factory=list)


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
