"""
Abstract: Request-local MCP authentication context for tool execution.
Out of scope: Bearer parsing, token exchange, and JWT validation.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

from knowledge_mcp.auth.verifier import AuthenticatedPrincipal


class MissingAuthContextError(RuntimeError):
    pass


_principal_context: ContextVar[AuthenticatedPrincipal | None] = ContextVar(
    "knowledge_mcp_principal",
    default=None,
)
_request_id_context: ContextVar[str | None] = ContextVar(
    "knowledge_mcp_request_id",
    default=None,
)


@dataclass(frozen=True)
class AuthContextTokens:
    principal: Token[AuthenticatedPrincipal | None]
    request_id: Token[str | None]


def set_auth_context(
    *,
    principal: AuthenticatedPrincipal,
    request_id: str,
) -> AuthContextTokens:
    return AuthContextTokens(
        principal=_principal_context.set(principal),
        request_id=_request_id_context.set(request_id),
    )


def reset_auth_context(tokens: AuthContextTokens) -> None:
    _principal_context.reset(tokens.principal)
    _request_id_context.reset(tokens.request_id)


def current_principal() -> AuthenticatedPrincipal:
    principal = _principal_context.get()
    if principal is None:
        raise MissingAuthContextError("MCP authentication context is not available.")
    return principal


async def load_current_principal() -> AuthenticatedPrincipal:
    return current_principal()


def current_request_id() -> str:
    return _request_id_context.get() or "unknown"
