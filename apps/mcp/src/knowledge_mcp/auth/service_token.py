"""
Abstract: Logto service-token verification for internal MCP HTTP endpoints.
Out of scope: Public MCP PAT exchange and browser session handling.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from knowledge_mcp.auth.verifier import (
    AccessTokenVerifier,
    TokenAuthenticationError,
    TokenVerifierSettings,
)


class ServiceTokenAuthenticationError(ValueError):
    pass


class ServiceTokenPrincipal(BaseModel):
    client_id: str = Field(min_length=1)
    scopes: frozenset[str]


class ServiceTokenVerifierSettings(BaseModel):
    issuer: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    discovery_url: str = Field(min_length=1)
    required_scope: str = Field(min_length=1)
    allowed_client_id: str = Field(min_length=1)
    http_timeout_seconds: float = Field(default=5.0, gt=0)


class ServiceTokenVerifier:
    def __init__(self, *, settings: ServiceTokenVerifierSettings) -> None:
        self._allowed_client_id = settings.allowed_client_id
        self._verifier = AccessTokenVerifier(
            settings=TokenVerifierSettings(
                issuer=settings.issuer,
                resource=settings.resource,
                discovery_url=settings.discovery_url,
                required_scopes=(settings.required_scope,),
                http_timeout_seconds=settings.http_timeout_seconds,
            )
        )

    async def verify_service_token(self, access_token: str) -> ServiceTokenPrincipal:
        try:
            principal = await self._verifier.verify_access_token(
                access_token,
                pat_fingerprint="pat_" + ("0" * 64),
            )
        except TokenAuthenticationError as exc:
            raise ServiceTokenAuthenticationError("Invalid service token.") from exc

        if principal.user_sub != self._allowed_client_id:
            raise ServiceTokenAuthenticationError("Service client is not allowed.")
        return ServiceTokenPrincipal(
            client_id=principal.user_sub,
            scopes=principal.scopes,
        )
