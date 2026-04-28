"""
Abstract: Internal HTTP endpoint for dashboard usage-summary reads.
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
from knowledge_mcp.usage.summary import (
    UsageSummaryRequest,
    UsageSummaryRow,
    dedupe_pat_fingerprints,
)


class UsageSummaryService(Protocol):
    async def get_summaries(self, pat_fingerprints: list[str]) -> list[UsageSummaryRow]: ...


class ServiceTokenVerifier(Protocol):
    async def verify_service_token(self, access_token: str) -> ServiceTokenPrincipal: ...


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message}},
        status_code=status_code,
    )


def create_usage_summary_endpoint(
    *,
    service: UsageSummaryService,
    service_token_verifier: ServiceTokenVerifier,
    max_batch_size: int,
) -> Callable[[Request], Awaitable[Response]]:
    async def endpoint(request: Request) -> Response:
        try:
            access_token = extract_bearer_token(request.headers.get("authorization"))
        except AuthenticationError:
            return _error(401, "usage_summary_auth_required", "Bearer token is required.")

        try:
            await service_token_verifier.verify_service_token(access_token)
        except ServiceTokenAuthenticationError:
            return _error(403, "usage_summary_forbidden", "Usage summary access is forbidden.")

        try:
            payload = UsageSummaryRequest.model_validate(await request.json())
        except ValidationError, ValueError:
            return _error(400, "usage_summary_invalid_request", "Usage summary request is invalid.")

        fingerprints = dedupe_pat_fingerprints(payload.pat_fingerprints)
        if len(fingerprints) > max_batch_size:
            return _error(400, "usage_summary_invalid_request", "Usage summary batch is too large.")

        summaries = await service.get_summaries(fingerprints)
        return JSONResponse(
            {"summaries": [summary.model_dump(mode="json", by_alias=True) for summary in summaries]}
        )

    return endpoint
