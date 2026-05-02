"""
Abstract: API entrypoint app factory and runtime wiring for FastAPI routes.
Out of scope: Domain business rules and persistence query logic.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

from core.error_http import (
    app_error_from_request_validation,
    headers_for_app_error,
    status_code_for_app_error,
)
from core.errors import AppError, InternalError
from entrypoints.api import providers as api_providers
from modules.ingestion.api import build_router as build_ingestion_router
from modules.knowledge_graph.api import build_router as build_knowledge_graph_router
from modules.search.api import build_router as build_search_router
from modules.taxonomy.api import build_router as build_taxonomy_router

logger = logging.getLogger(__name__)
API_V1_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge API", version="0.1.0")
    app.include_router(
        build_search_router(get_search_service=api_providers.get_search_service),
        prefix=API_V1_PREFIX,
    )
    app.include_router(
        build_ingestion_router(get_ingestion_service=api_providers.get_ingestion_service),
        prefix=API_V1_PREFIX,
    )
    app.include_router(
        build_knowledge_graph_router(
            get_knowledge_graph_service=api_providers.get_knowledge_graph_service
        ),
        prefix=API_V1_PREFIX,
    )
    app.include_router(
        build_taxonomy_router(get_taxonomy_service=api_providers.get_taxonomy_service),
        prefix=API_V1_PREFIX,
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
        status_code = status_code_for_app_error(exc)
        logger.warning(
            "app.error",
            extra={
                "request_id": request_id,
                "code": exc.code.value,
                "http_status": status_code,
                "path": request.url.path,
                "method": request.method,
                "exception_class": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=status_code,
            headers=headers_for_app_error(exc),
            content=exc.to_response_envelope(request_id=request_id).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        normalized_error = app_error_from_request_validation(exc)
        status_code = status_code_for_app_error(normalized_error)
        request_id = request.state.request_id
        logger.warning(
            "app.validation_error",
            extra={
                "request_id": request_id,
                "code": normalized_error.code.value,
                "http_status": status_code,
                "path": request.url.path,
                "method": request.method,
                "exception_class": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=status_code,
            content=normalized_error.to_response_envelope(request_id=request_id).model_dump(
                mode="json"
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.state.request_id
        wrapped = InternalError(
            message="Unexpected server error.",
            hint="Retry later with the provided request_id.",
        )
        logger.exception(
            "app.unexpected_error",
            extra={
                "request_id": request_id,
                "code": wrapped.code.value,
                "http_status": 500,
                "path": request.url.path,
                "method": request.method,
                "exception_class": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content=wrapped.to_response_envelope(request_id=request_id).model_dump(mode="json"),
        )

    return app


__all__ = ["create_app"]
