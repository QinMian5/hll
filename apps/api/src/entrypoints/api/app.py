"""
Abstract: API entrypoint app factory and runtime wiring for FastAPI routes.
Out of scope: Domain business rules and persistence query logic.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from core.errors import AppError, InternalError
from entrypoints.api import providers as api_providers
from modules.ingestion.api import build_router as build_ingestion_router
from modules.search.api import build_router as build_search_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge API", version="0.1.0")
    app.include_router(build_search_router(get_search_service=api_providers.get_search_service))
    app.include_router(
        build_ingestion_router(get_ingestion_service=api_providers.get_ingestion_service)
    )

    @app.middleware("http")
    async def attach_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", "").strip() or f"req_{uuid4().hex}"
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = request.state.request_id
        payload = exc.to_response_payload(request_id=request_id).model_dump()
        status_code = 400
        logger.warning(
            "app.error",
            extra={"request_id": request_id, "code": exc.code.value},
        )
        return JSONResponse(status_code=status_code, content=payload)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.state.request_id
        wrapped = InternalError(
            message="Unexpected server error.",
            hint="Retry later with the provided request_id.",
        )
        logger.exception(
            "app.unexpected_error",
            extra={"request_id": request_id, "exception_class": exc.__class__.__name__},
        )
        return JSONResponse(
            status_code=500,
            content=wrapped.to_response_payload(request_id=request_id).model_dump(),
        )

    return app


__all__ = ["create_app"]
