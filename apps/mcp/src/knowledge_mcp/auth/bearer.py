"""
Abstract: Bearer authorization parsing for the public Knowledge MCP service.
Out of scope: Token exchange, token validation, and quota accounting.
"""

from __future__ import annotations


class AuthenticationError(ValueError):
    pass


def extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise AuthenticationError("Missing bearer token.")

    scheme, separator, token = authorization.partition(" ")
    if separator == "" or scheme.lower() != "bearer":
        raise AuthenticationError("Missing bearer token.")

    token = token.strip()
    if not token:
        raise AuthenticationError("Missing bearer token.")

    return token
