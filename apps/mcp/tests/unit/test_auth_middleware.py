"""
Abstract: Unit tests for MCP request authentication context middleware.
Out of scope: Live Logto, Redis, PostgreSQL, and MCP tool execution.
"""

from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from knowledge_mcp.auth.context import current_mcp_session_id, current_principal, current_request_id
from knowledge_mcp.auth.fingerprint import fingerprint_pat
from knowledge_mcp.auth.middleware import AuthContextMiddleware
from knowledge_mcp.auth.token_exchange import (
    TokenExchangeAuthenticationError,
    TokenExchangeResult,
)
from knowledge_mcp.auth.verifier import AuthenticatedPrincipal


class FakeTokenExchangeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def exchange_pat(
        self,
        pat: str,
        *,
        pat_fingerprint: str | None = None,
    ) -> TokenExchangeResult:
        self.calls.append((pat, pat_fingerprint))
        return TokenExchangeResult(access_token="access-token", expires_in=300)


class RejectingTokenExchangeClient:
    async def exchange_pat(
        self,
        pat: str,
        *,
        pat_fingerprint: str | None = None,
    ) -> TokenExchangeResult:
        raise TokenExchangeAuthenticationError("rejected")


class FakeAccessTokenVerifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def verify_access_token(
        self,
        access_token: str,
        *,
        pat_fingerprint: str,
    ) -> AuthenticatedPrincipal:
        self.calls.append((access_token, pat_fingerprint))
        return AuthenticatedPrincipal(
            user_sub="user_123",
            scopes=frozenset({"search:execute"}),
            pat_fingerprint=pat_fingerprint,
        )


async def _context_route(_: object) -> Response:
    principal = current_principal()
    return JSONResponse(
        {
            "mcp_session_id": current_mcp_session_id(),
            "request_id": current_request_id(),
            "user_sub": principal.user_sub,
            "pat_fingerprint": principal.pat_fingerprint,
        }
    )


async def _health_route(_: object) -> Response:
    return JSONResponse({"status": "ok"})


def _build_app(
    *,
    token_exchange_client: object | None = None,
    allowed_origins: tuple[str, ...] = ("https://app.example.com",),
) -> tuple[Starlette, FakeTokenExchangeClient, FakeAccessTokenVerifier]:
    exchange = token_exchange_client or FakeTokenExchangeClient()
    verifier = FakeAccessTokenVerifier()
    app = Starlette(
        routes=[
            Route("/healthz", _health_route, methods=["GET"]),
            Route("/mcp", _context_route, methods=["GET"]),
        ]
    )
    app.add_middleware(
        AuthContextMiddleware,
        token_exchange_client=exchange,
        access_token_verifier=verifier,
        pat_fingerprint_secret="x" * 32,
        allowed_origins=allowed_origins,
    )
    return app, exchange, verifier


@pytest.mark.anyio
async def test_middleware_does_not_authenticate_health_checks() -> None:
    app, exchange, verifier = _build_app()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert exchange.calls == []
    assert verifier.calls == []


@pytest.mark.anyio
async def test_middleware_exchanges_pat_and_sets_request_context() -> None:
    app, exchange, verifier = _build_app()
    expected_fingerprint = fingerprint_pat("pat_secret_value", secret="x" * 32)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/mcp",
            headers={
                "authorization": "Bearer pat_secret_value",
                "origin": "https://app.example.com",
                "mcp-session-id": "mcp-session-1",
                "x-request-id": "request-1",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "mcp_session_id": "mcp-session-1",
        "request_id": "request-1",
        "user_sub": "user_123",
        "pat_fingerprint": expected_fingerprint,
    }
    assert exchange.calls == [("pat_secret_value", expected_fingerprint)]
    assert verifier.calls == [("access-token", expected_fingerprint)]


@pytest.mark.anyio
async def test_middleware_rejects_disallowed_origin_before_token_exchange() -> None:
    app, exchange, _ = _build_app()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/mcp",
            headers={
                "authorization": "Bearer pat_secret_value",
                "origin": "https://evil.example.com",
            },
        )

    assert response.status_code == 403
    assert exchange.calls == []


@pytest.mark.anyio
async def test_middleware_maps_missing_bearer_to_unauthorized() -> None:
    app, _, _ = _build_app()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/mcp")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_middleware_never_returns_raw_pat_in_authentication_failures() -> None:
    app, _, _ = _build_app(token_exchange_client=RejectingTokenExchangeClient())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/mcp",
            headers={"authorization": "Bearer pat_secret_value"},
        )

    assert response.status_code == 401
    assert "pat_secret_value" not in response.text
