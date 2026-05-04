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


class TaxonomyNodeRecord(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    name: NonEmptyString
    route_slug: NonEmptyString
    depth: int = Field(ge=0)


class TaxonomyTreeNode(BaseModel):
    model_config = ConfigDict(strict=True)

    id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    name: NonEmptyString
    route_slug: NonEmptyString
    depth: int = Field(ge=0)
    children: list[TaxonomyTreeNode] = Field(default_factory=list)


class TaxonomyAssignmentRecord(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    id: int = Field(gt=0)
    node_id: int = Field(gt=0)
    taxonomy_node: TaxonomyNodeRecord
    assigned_at: datetime


TaxonomyScopeKind = Literal["taxonomy_node", "virtual_unclassified"]
TaxonomyCardScopeLayoutStatus = Literal["ready", "refreshing"]


class TaxonomyScopeIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    scope_kind: TaxonomyScopeKind
    taxonomy_node_id: int = Field(gt=0)


class TaxonomyScopeAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    node_id: int = Field(gt=0)
    taxonomy_node_id: int = Field(gt=0)


class TaxonomyAssignmentCount(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    taxonomy_node_id: int = Field(gt=0)
    card_count: int = Field(ge=0)


class TaxonomyCardScopeWorldBounds(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_x: float
    min_y: float
    max_x: float
    max_y: float


class TaxonomyCardScopeLayoutNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(gt=0)
    scope: Literal["inner", "outer"]
    x: float
    y: float


class TaxonomyCardScopeLayoutEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_node_id: int = Field(gt=0)
    target_node_id: int = Field(gt=0)
    strength: float = Field(ge=0.0, le=1.0)


class TaxonomyCardScopeLayout(BaseModel):
    model_config = ConfigDict(frozen=True)

    layout_version: str = Field(min_length=1)
    generated_at: datetime
    world_bounds: TaxonomyCardScopeWorldBounds
    nodes: list[TaxonomyCardScopeLayoutNode]
    edges: list[TaxonomyCardScopeLayoutEdge]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


class TaxonomyCardScopeLayoutReadModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    input_fingerprint: str = Field(min_length=1)
    layout: TaxonomyCardScopeLayout


class TaxonomyCardScopeLayoutComputeClaim(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    scope_identity: TaxonomyScopeIdentity
    input_fingerprint: str = Field(min_length=1)


class TaxonomyCardScopeLayoutSlice(BaseModel):
    model_config = ConfigDict(frozen=True)

    layout_version: str = Field(min_length=1)
    requested_bounds: TaxonomyCardScopeWorldBounds
    nodes: list[TaxonomyCardScopeLayoutNode]
    edges: list[TaxonomyCardScopeLayoutEdge]
