"""
Abstract: FastAPI route contract for read-only card search requests.
Out of scope: Search dependency construction and knowledge-domain internals.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Query

from modules.search.schema import SearchResponse
from modules.search.service import SearchService

SearchServiceProvider = Callable[..., SearchService]


def build_router(*, get_search_service: SearchServiceProvider) -> APIRouter:
    router = APIRouter(tags=["search"])

    @router.get("/search", response_model=SearchResponse)
    async def search_cards(
        query: str = Query(min_length=1),
        search_service: SearchService = Depends(get_search_service),
    ) -> SearchResponse:
        return await search_service.search(query)

    return router
