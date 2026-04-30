"""
Abstract: Pydantic DTOs for taxonomy bootstrap, tree reads, and final assignments.
Out of scope: SQLAlchemy persistence mapping and HTTP transport contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

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
    route_slug: NonEmptyString
    depth: int = Field(ge=0)
    is_leaf: bool


class TaxonomyTreeNode(BaseModel):
    model_config = ConfigDict(strict=True)

    id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    name: NonEmptyString
    route_slug: NonEmptyString
    depth: int = Field(ge=0)
    is_leaf: bool
    children: list[TaxonomyTreeNode] = Field(default_factory=list)


class TaxonomyAssignmentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: int = Field(gt=0)
    node_id: int = Field(gt=0)
    taxonomy_node: TaxonomyNodeRecord
    assigned_at: datetime


class TaxonomyLeafAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    taxonomy_leaf_id: int = Field(gt=0)


class TaxonomyLeafAssignmentCount(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    taxonomy_leaf_id: int = Field(gt=0)
    card_count: int = Field(ge=0)


class TaxonomyLeafWorldBounds(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_x: float
    min_y: float
    max_x: float
    max_y: float


class TaxonomyLeafLayoutNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(gt=0)
    scope: Literal["inner", "outer"]
    x: float
    y: float


class TaxonomyLeafLayoutEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_node_id: int = Field(gt=0)
    target_node_id: int = Field(gt=0)
    strength: float = Field(ge=0.0, le=1.0)


class TaxonomyLeafLayout(BaseModel):
    model_config = ConfigDict(frozen=True)

    layout_version: str = Field(min_length=1)
    generated_at: datetime
    world_bounds: TaxonomyLeafWorldBounds
    nodes: list[TaxonomyLeafLayoutNode]
    edges: list[TaxonomyLeafLayoutEdge]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


class TaxonomyLeafLayoutSlice(BaseModel):
    model_config = ConfigDict(frozen=True)

    layout_version: str = Field(min_length=1)
    requested_bounds: TaxonomyLeafWorldBounds
    nodes: list[TaxonomyLeafLayoutNode]
    edges: list[TaxonomyLeafLayoutEdge]
