"""
Abstract: FastAPI route contract for taxonomy root/node drill-down view requests.
Out of scope: Taxonomy persistence queries and classification orchestration logic.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends

from modules.taxonomy.schema import (
    TaxonomyLeafLayoutSliceResponse,
    TaxonomyLeafNodeDetailsRequest,
    TaxonomyLeafNodeDetailsResponse,
    TaxonomyLeafNodeTitlesRequest,
    TaxonomyLeafNodeTitlesResponse,
    TaxonomyNodeViewResponse,
    TaxonomyRootViewResponse,
)
from modules.taxonomy.service import TaxonomyService

TaxonomyServiceProvider = Callable[..., TaxonomyService]


def build_router(*, get_taxonomy_service: TaxonomyServiceProvider) -> APIRouter:
    router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])

    @router.get("/view/root", response_model=TaxonomyRootViewResponse)
    async def get_root_view(
        taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
    ) -> TaxonomyRootViewResponse:
        return await taxonomy_service.get_root_view()

    @router.get("/view/nodes/{node_id}", response_model=TaxonomyNodeViewResponse)
    async def get_node_view(
        node_id: int,
        taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
    ) -> TaxonomyNodeViewResponse:
        return await taxonomy_service.get_node_view(node_id=node_id)

    @router.get("/view/path/{route_path:path}", response_model=TaxonomyNodeViewResponse)
    async def get_path_view(
        route_path: str,
        taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
    ) -> TaxonomyNodeViewResponse:
        return await taxonomy_service.get_node_view_by_route_path(route_path=route_path)

    @router.get(
        "/view/leaves/{node_id}/layout",
        response_model=TaxonomyLeafLayoutSliceResponse,
    )
    async def get_leaf_layout_slice(
        node_id: int,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
    ) -> TaxonomyLeafLayoutSliceResponse:
        return await taxonomy_service.get_leaf_layout_slice(
            node_id=node_id,
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
        )

    @router.post(
        "/view/leaves/{node_id}/details",
        response_model=TaxonomyLeafNodeDetailsResponse,
    )
    async def get_leaf_node_details(
        node_id: int,
        request: TaxonomyLeafNodeDetailsRequest,
        taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
    ) -> TaxonomyLeafNodeDetailsResponse:
        return await taxonomy_service.get_leaf_node_details(
            node_id=node_id,
            node_ids=request.node_ids,
        )

    @router.post(
        "/view/leaves/{node_id}/titles",
        response_model=TaxonomyLeafNodeTitlesResponse,
    )
    async def get_leaf_node_titles(
        node_id: int,
        request: TaxonomyLeafNodeTitlesRequest,
        taxonomy_service: TaxonomyService = Depends(get_taxonomy_service),
    ) -> TaxonomyLeafNodeTitlesResponse:
        return await taxonomy_service.get_leaf_node_titles(
            node_id=node_id,
            node_ids=request.node_ids,
        )

    return router
