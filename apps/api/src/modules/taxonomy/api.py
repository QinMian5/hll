"""
Abstract: FastAPI route contract for taxonomy root/node drill-down view requests.
Out of scope: Taxonomy persistence queries and classification orchestration logic.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends

from modules.taxonomy.schema import (
    TaxonomyLeafNodeDetailsRequest,
    TaxonomyLeafNodeDetailsResponse,
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

    return router
