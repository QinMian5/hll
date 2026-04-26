"""
Abstract: Shared OAuth client-credentials access-token provider for job-queue calls.
Out of scope: Job submission behavior and token introspection.
"""

from __future__ import annotations

import time
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict


class AccessTokenProvider(Protocol):
    async def get_access_token(self) -> str: ...

    async def aclose(self) -> None: ...


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str
    expires_in: int
    token_type: str


class ClientCredentialsTokenProvider:
    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        resource: str,
        scope: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._resource = resource
        self._scope = scope
        self._client = httpx.AsyncClient(transport=transport)
        self._access_token: str | None = None
        self._expires_at = 0.0

    async def get_access_token(self) -> str:
        if self._access_token is not None and time.monotonic() < self._expires_at:
            return self._access_token

        response = await self._client.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "resource": self._resource,
                "scope": self._scope,
            },
        )
        response.raise_for_status()
        token = TokenResponse.model_validate(response.json())
        self._access_token = token.access_token
        self._expires_at = time.monotonic() + max(token.expires_in - 60, 0)
        return token.access_token

    async def aclose(self) -> None:
        await self._client.aclose()


__all__ = ["AccessTokenProvider", "ClientCredentialsTokenProvider"]
