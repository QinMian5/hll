"""
Abstract: Pydantic DTOs for taxonomy bootstrap, tree reads, and final assignments.
Out of scope: SQLAlchemy persistence mapping and HTTP transport contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TaxonomyPath = tuple[NonEmptyString, ...]


class TaxonomyImportNode(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    path: TaxonomyPath = Field(min_length=1)
    parent_path: TaxonomyPath | None = None
    name: NonEmptyString
    depth: int = Field(ge=0)
    is_leaf: bool


class TaxonomyNodeRecord(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    name: NonEmptyString
    depth: int = Field(ge=0)
    is_leaf: bool


class TaxonomyTreeNode(BaseModel):
    model_config = ConfigDict(strict=True)

    id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    name: NonEmptyString
    depth: int = Field(ge=0)
    is_leaf: bool
    children: list[TaxonomyTreeNode] = Field(default_factory=list)


class TaxonomyAssignmentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: int = Field(gt=0)
    node_id: int = Field(gt=0)
    taxonomy_node: TaxonomyNodeRecord
    assigned_at: datetime


class TaxonomySemanticMapAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    taxonomy_leaf_id: int = Field(gt=0)
