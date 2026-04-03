"""
Abstract: FastAPI route wiring for ingestion request validation and accepted
responses.
Out of scope: Queue transport implementation and worker execution details.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, Request, status

from modules.ingestion.schema import IngestionAcceptedResponse, IngestionCreateRequest
from modules.ingestion.service import IngestionService

IngestionServiceProvider = Callable[..., IngestionService]


def build_router(*, get_ingestion_service: IngestionServiceProvider) -> APIRouter:
    router = APIRouter(tags=["ingestions"])

    @router.post(
        "/cards",
        response_model=IngestionAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def create_ingestion(
        payload: IngestionCreateRequest,
        request: Request,
        service: IngestionService = Depends(get_ingestion_service),
    ) -> IngestionAcceptedResponse:
        return await service.accept(
            payload=payload,
            request_id=request.state.request_id,
        )

    return router
