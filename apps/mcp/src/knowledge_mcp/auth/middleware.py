"""
Abstract: ASGI middleware for MCP Bearer PAT authentication and request context.
Out of scope: MCP tool execution, quota reservation, and usage-ledger writes.
"""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from knowledge_mcp.auth.bearer import AuthenticationError, extract_bearer_token
from knowledge_mcp.auth.context import reset_auth_context, set_auth_context
from knowledge_mcp.auth.fingerprint import fingerprint_pat
from knowledge_mcp.auth.token_exchange import (
    TokenExchangeAuthenticationError,
    TokenExchangeInfrastructureError,
    TokenExchangeResult,
)
from knowledge_mcp.auth.verifier import (
    AuthenticatedPrincipal,
    TokenAuthenticationError,
    TokenVerifierInfrastructureError,
)


class TokenExchangeClient(Protocol):
    async def exchange_pat(
        self,
        pat: str,
        *,
        pat_fingerprint: str | None = None,
    ) -> TokenExchangeResult: ...


class AccessTokenVerifier(Protocol):
    async def verify_access_token(
        self,
        access_token: str,
        *,
        pat_fingerprint: str,
    ) -> AuthenticatedPrincipal: ...


def is_origin_allowed(origin: str | None, *, allowed_origins: tuple[str, ...]) -> bool:
    if origin in (None, ""):
        return True
    return origin in allowed_origins


class AuthContextMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        token_exchange_client: TokenExchangeClient,
        access_token_verifier: AccessTokenVerifier,
        pat_fingerprint_secret: str,
        allowed_origins: tuple[str, ...],
        protected_path_prefix: str = "/mcp",
    ) -> None:
        self._app = app
        self._token_exchange_client = token_exchange_client
        self._access_token_verifier = access_token_verifier
        self._pat_fingerprint_secret = pat_fingerprint_secret
        self._allowed_origins = allowed_origins
        self._protected_path_prefix = protected_path_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path")
        if not isinstance(path, str) or not path.startswith(self._protected_path_prefix):
            await self._app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        if not is_origin_allowed(headers.get("origin"), allowed_origins=self._allowed_origins):
            await self._send_error(
                scope,
                receive,
                send,
                status_code=403,
                code="origin_not_allowed",
            )
            return

        try:
            principal = await self._authenticate(headers)
        except (
            AuthenticationError,
            TokenExchangeAuthenticationError,
            TokenAuthenticationError,
        ):
            await self._send_error(
                scope,
                receive,
                send,
                status_code=401,
                code="unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
            return
        except TokenExchangeInfrastructureError, TokenVerifierInfrastructureError:
            await self._send_error(
                scope,
                receive,
                send,
                status_code=503,
                code="authentication_unavailable",
            )
            return

        request_id = headers.get("x-request-id") or str(uuid4())
        mcp_session_id = headers.get("mcp-session-id") or str(uuid4())
        context_tokens = set_auth_context(
            principal=principal,
            request_id=request_id,
            mcp_session_id=mcp_session_id,
        )
        try:
            await self._app(scope, receive, send)
        finally:
            reset_auth_context(context_tokens)

    async def _authenticate(self, headers: Headers) -> AuthenticatedPrincipal:
        pat = extract_bearer_token(headers.get("authorization"))
        pat_fingerprint = fingerprint_pat(pat, secret=self._pat_fingerprint_secret)
        exchange_result = await self._token_exchange_client.exchange_pat(
            pat,
            pat_fingerprint=pat_fingerprint,
        )
        return await self._access_token_verifier.verify_access_token(
            exchange_result.access_token,
            pat_fingerprint=pat_fingerprint,
        )

    async def _send_error(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        code: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        response = JSONResponse(
            {"error": code},
            status_code=status_code,
            headers=headers,
        )
        await response(scope, receive, send)
