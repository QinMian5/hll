"""
Abstract: ASGI application factory for the public Knowledge MCP service.
Out of scope: MCP tool behavior, authentication policy decisions, and deployment orchestration.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Mount, Route
from starlette.types import Lifespan

from knowledge_mcp.auth.middleware import AuthContextMiddleware, is_origin_allowed
from knowledge_mcp.config import Settings, load_settings
from knowledge_mcp.internal_quota_summary import create_quota_summary_endpoint
from knowledge_mcp.internal_usage_summary import create_usage_summary_endpoint
from knowledge_mcp.runtime import RuntimeResources, build_runtime_resources
from knowledge_mcp.search_tool import SearchTool
from knowledge_mcp.server import create_mcp_server

__all__ = ["create_app", "healthz", "is_origin_allowed"]


async def healthz(_: object) -> Response:
    return JSONResponse({"status": "ok"})


def create_app(
    *,
    settings: Settings | None = None,
    search_tool: SearchTool | None = None,
) -> Starlette:
    runtime_resources: RuntimeResources | None = None
    middleware: list[Middleware] = []

    resolved_settings = settings or load_settings()
    if search_tool is None:
        runtime_resources = build_runtime_resources(resolved_settings)
        search_tool = runtime_resources.search_tool
        middleware.append(
            Middleware(
                AuthContextMiddleware,
                token_exchange_client=runtime_resources.auth_middleware_kwargs[
                    "token_exchange_client"
                ],
                access_token_verifier=runtime_resources.auth_middleware_kwargs[
                    "access_token_verifier"
                ],
                pat_fingerprint_secret=runtime_resources.auth_middleware_kwargs[
                    "pat_fingerprint_secret"
                ],
                allowed_origins=runtime_resources.auth_middleware_kwargs["allowed_origins"],
            )
        )

    routes: list[BaseRoute] = [Route("/healthz", healthz, methods=["GET"])]
    if runtime_resources is not None:
        routes.append(
            Route(
                "/internal/dashboard/usage-summary",
                create_usage_summary_endpoint(
                    service=runtime_resources.usage_summary_service,
                    service_token_verifier=(runtime_resources.usage_summary_service_token_verifier),
                    max_batch_size=runtime_resources.usage_summary_max_batch_size,
                ),
                methods=["POST"],
            )
        )
        routes.append(
            Route(
                "/internal/dashboard/quota-summary",
                create_quota_summary_endpoint(
                    service=runtime_resources.quota_summary_service,
                    service_token_verifier=(runtime_resources.usage_summary_service_token_verifier),
                ),
                methods=["POST"],
            )
        )

    mcp_server = create_mcp_server(search_tool=search_tool)
    routes.append(Mount("/mcp", app=mcp_server.streamable_http_app()))
    return Starlette(
        routes=routes,
        middleware=middleware,
        lifespan=_runtime_lifespan(runtime_resources),
    )


def _runtime_lifespan(resources: RuntimeResources | None) -> Lifespan[Starlette] | None:
    if resources is None:
        return None

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await resources.aclose()

    return lifespan
