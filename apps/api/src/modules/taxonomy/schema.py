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


class TaxonomyViewScopeResponse(TaxonomyViewResponseModel):
    scope_kind: Literal["taxonomy_node", "virtual_unclassified"]
    taxonomy_node_id: int | None = Field(default=None, gt=0)
    parent_taxonomy_node_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1)
    route_slug: str = Field(min_length=1)
    route_path: str
    depth: int = Field(ge=0)


class TaxonomyViewChildResponse(TaxonomyViewScopeResponse):
    node_kind: Literal["branch", "card_scope"]
    descendant_card_count: int = Field(ge=0)


class TaxonomyRootViewResponse(TaxonomyViewResponseModel):
    breadcrumb: list[TaxonomyViewScopeResponse]
    children: list[TaxonomyViewChildResponse]


class TaxonomyCardScopeGraphNodeResponse(TaxonomyViewResponseModel):
    id: int = Field(gt=0)
    scope: Literal["inner", "outer"]


class TaxonomyCardScopeWorldBoundsResponse(TaxonomyViewResponseModel):
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class TaxonomyCardScopeLayoutNodeResponse(TaxonomyCardScopeGraphNodeResponse):
    x: float
    y: float


class TaxonomyCardScopeNodeDetailResponse(TaxonomyViewResponseModel):
    id: int = Field(gt=0)
    current_version: int = Field(gt=0)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class TaxonomyCardScopeNodeTitleResponse(TaxonomyViewResponseModel):
    id: int = Field(gt=0)
    title: str = Field(min_length=1)


class TaxonomyCardScopeNodeDetailsRequest(TaxonomyViewResponseModel):
    route_path: str
    node_ids: list[int] = Field(default_factory=list)


class TaxonomyCardScopeNodeDetailsResponse(TaxonomyViewResponseModel):
    nodes: list[TaxonomyCardScopeNodeDetailResponse]


class TaxonomyCardScopeNodeTitlesRequest(TaxonomyViewResponseModel):
    route_path: str
    node_ids: list[int] = Field(default_factory=list)


class TaxonomyCardScopeNodeTitlesResponse(TaxonomyViewResponseModel):
    nodes: list[TaxonomyCardScopeNodeTitleResponse]


type TaxonomyCardScopeGraphEdgeResponse = tuple[
    Annotated[int, Field(gt=0)],
    Annotated[int, Field(gt=0)],
    Annotated[float, Field(ge=0.0, le=1.0)],
]


class TaxonomyNodeBranchViewResponse(TaxonomyViewResponseModel):
    node_kind: Literal["branch"]
    current_scope: TaxonomyViewScopeResponse
    breadcrumb: list[TaxonomyViewScopeResponse]
    children: list[TaxonomyViewChildResponse]


class TaxonomyNodeCardScopeViewResponse(TaxonomyViewResponseModel):
    node_kind: Literal["card_scope"]
    current_scope: TaxonomyViewScopeResponse
    breadcrumb: list[TaxonomyViewScopeResponse]
    layout_version: str = Field(min_length=1)
    world_bounds: TaxonomyCardScopeWorldBoundsResponse
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    generated_at: datetime


class TaxonomyCardScopeLayoutSliceResponse(TaxonomyViewResponseModel):
    scope_kind: Literal["taxonomy_node", "virtual_unclassified"]
    taxonomy_node_id: int | None = Field(default=None, gt=0)
    parent_taxonomy_node_id: int | None = Field(default=None, gt=0)
    route_path: str
    layout_version: str = Field(min_length=1)
    requested_bounds: TaxonomyCardScopeWorldBoundsResponse
    nodes: list[TaxonomyCardScopeLayoutNodeResponse]
    edges: list[TaxonomyCardScopeGraphEdgeResponse]


type TaxonomyNodeViewResponse = Annotated[
    TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse,
    Field(discriminator="node_kind"),
]
