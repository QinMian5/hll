"""
Abstract: FastAPI route wiring for ingestion request validation and accepted
responses.
Out of scope: Queue transport implementation and worker execution details.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from core.errors import ErrorEnvelope
from modules.ingestion.schema import IngestionAcceptedResponse, IngestionCreateRequest
from modules.ingestion.service import IngestionService

IngestionServiceProvider = Callable[..., IngestionService]


def build_router(*, get_ingestion_service: IngestionServiceProvider) -> APIRouter:
    router = APIRouter(tags=["ingestions"])

    @router.post(
        "/cards",
        response_model=IngestionAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
        responses={status.HTTP_409_CONFLICT: {"model": ErrorEnvelope}},
    )
    async def create_ingestion(
        payload: IngestionCreateRequest,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        service: IngestionService = Depends(get_ingestion_service),
    ) -> IngestionAcceptedResponse:
        return await service.accept(
            payload=payload,
            request_id=request.state.request_id,
            idempotency_key=idempotency_key,
        )

    return router
