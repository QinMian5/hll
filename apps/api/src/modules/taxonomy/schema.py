"""
Abstract: Pydantic response models for taxonomy root/node drill-down view APIs.
Out of scope: Taxonomy persistence queries and classification orchestration rules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class TaxonomyViewResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaxonomyViewNodeResponse(TaxonomyViewResponseModel):
    id: int = Field(gt=0)
    parent_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1)
    route_slug: str = Field(min_length=1)
    route_path: str
    depth: int = Field(ge=0)
    is_leaf: bool


class TaxonomyViewChildResponse(TaxonomyViewNodeResponse):
    descendant_card_count: int = Field(ge=0)


class TaxonomyRootViewResponse(TaxonomyViewResponseModel):
    breadcrumb: list[TaxonomyViewNodeResponse]
    children: list[TaxonomyViewChildResponse]


class TaxonomyLeafGraphNodeResponse(TaxonomyViewResponseModel):
    id: int = Field(gt=0)
    scope: Literal["inner", "outer"]


class TaxonomyLeafWorldBoundsResponse(TaxonomyViewResponseModel):
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class TaxonomyLeafLayoutNodeResponse(TaxonomyLeafGraphNodeResponse):
    x: float
    y: float


class TaxonomyLeafNodeDetailResponse(TaxonomyViewResponseModel):
    id: int = Field(gt=0)
    current_version: int = Field(gt=0)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class TaxonomyLeafNodeTitleResponse(TaxonomyViewResponseModel):
    id: int = Field(gt=0)
    title: str = Field(min_length=1)


class TaxonomyLeafNodeDetailsRequest(TaxonomyViewResponseModel):
    node_ids: list[int] = Field(default_factory=list)


class TaxonomyLeafNodeDetailsResponse(TaxonomyViewResponseModel):
    nodes: list[TaxonomyLeafNodeDetailResponse]


class TaxonomyLeafNodeTitlesRequest(TaxonomyViewResponseModel):
    node_ids: list[int] = Field(default_factory=list)


class TaxonomyLeafNodeTitlesResponse(TaxonomyViewResponseModel):
    nodes: list[TaxonomyLeafNodeTitleResponse]


type TaxonomyLeafGraphEdgeResponse = tuple[
    Annotated[int, Field(gt=0)],
    Annotated[int, Field(gt=0)],
    Annotated[float, Field(ge=0.0, le=1.0)],
]


class TaxonomyNodeBranchViewResponse(TaxonomyViewResponseModel):
    node_kind: Literal["branch"]
    current_node: TaxonomyViewNodeResponse
    breadcrumb: list[TaxonomyViewNodeResponse]
    children: list[TaxonomyViewChildResponse]


class TaxonomyNodeLeafViewResponse(TaxonomyViewResponseModel):
    node_kind: Literal["leaf"]
    current_node: TaxonomyViewNodeResponse
    breadcrumb: list[TaxonomyViewNodeResponse]
    layout_version: str = Field(min_length=1)
    world_bounds: TaxonomyLeafWorldBoundsResponse
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    generated_at: datetime


class TaxonomyLeafLayoutSliceResponse(TaxonomyViewResponseModel):
    leaf_id: int = Field(gt=0)
    layout_version: str = Field(min_length=1)
    requested_bounds: TaxonomyLeafWorldBoundsResponse
    nodes: list[TaxonomyLeafLayoutNodeResponse]
    edges: list[TaxonomyLeafGraphEdgeResponse]


type TaxonomyNodeViewResponse = Annotated[
    TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
    Field(discriminator="node_kind"),
]
