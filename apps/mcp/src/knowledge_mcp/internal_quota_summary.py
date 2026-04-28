"""
Abstract: Internal HTTP endpoint for dashboard quota-summary reads.
Out of scope: Public MCP protocol transport and Logto PAT lifecycle operations.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from knowledge_mcp.auth.bearer import AuthenticationError, extract_bearer_token
from knowledge_mcp.auth.service_token import ServiceTokenAuthenticationError, ServiceTokenPrincipal
from knowledge_mcp.quota.store import QuotaSummary
from knowledge_mcp.quota.summary import QuotaSummaryRequest, QuotaSummaryResponse


class QuotaSummaryService(Protocol):
    async def get_summary(self, *, user_sub: str) -> QuotaSummary: ...


class ServiceTokenVerifier(Protocol):
    async def verify_service_token(self, access_token: str) -> ServiceTokenPrincipal: ...


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message}},
        status_code=status_code,
    )


def create_quota_summary_endpoint(
    *,
    service: QuotaSummaryService,
    service_token_verifier: ServiceTokenVerifier,
) -> Callable[[Request], Awaitable[Response]]:
    async def endpoint(request: Request) -> Response:
        try:
            access_token = extract_bearer_token(request.headers.get("authorization"))
        except AuthenticationError:
            return _error(401, "quota_summary_auth_required", "Bearer token is required.")

        try:
            await service_token_verifier.verify_service_token(access_token)
        except ServiceTokenAuthenticationError:
            return _error(403, "quota_summary_forbidden", "Quota summary access is forbidden.")

        try:
            payload = QuotaSummaryRequest.model_validate(await request.json())
        except ValidationError, ValueError:
            return _error(400, "quota_summary_invalid_request", "Quota summary request is invalid.")

        summary = await service.get_summary(user_sub=payload.user_sub)
        response = QuotaSummaryResponse.from_summary(summary)
        return JSONResponse(response.model_dump(mode="json", by_alias=True))

    return endpoint
