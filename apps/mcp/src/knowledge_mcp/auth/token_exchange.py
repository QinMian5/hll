"""
Abstract: Logto Personal Access Token exchange for MCP access tokens.
Out of scope: JWT claim validation and MCP protocol tool execution.
"""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from redis.asyncio import Redis

JsonObjectAdapter = TypeAdapter(dict[str, object])

TOKEN_EXCHANGE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
LOGTO_PAT_TOKEN_TYPE = "urn:logto:token-type:personal_access_token"


class TokenExchangeAuthenticationError(ValueError):
    pass


class TokenExchangeInfrastructureError(RuntimeError):
    pass


class TokenExchangeSettings(BaseModel):
    token_url: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    scopes: tuple[str, ...] = Field(min_length=1)
    http_timeout_seconds: float = Field(default=5.0, gt=0)
    token_cache_ttl_seconds: int = Field(default=300, ge=1)


class TokenExchangeResult(BaseModel):
    access_token: str = Field(min_length=1)
    issued_token_type: str = ACCESS_TOKEN_TYPE
    token_type: str = "Bearer"
    expires_in: int = Field(gt=0)
    scope: str | None = None


class TokenExchangeClient:
    def __init__(
        self,
        *,
        settings: TokenExchangeSettings,
        http_client: httpx.AsyncClient | None = None,
        redis_client: Redis | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client
        self._redis_client = redis_client

    async def exchange_pat(
        self,
        pat: str,
        *,
        pat_fingerprint: str | None = None,
    ) -> TokenExchangeResult:
        cache_key = self._cache_key(pat_fingerprint)
        if cache_key is not None:
            cached = await self._load_cached_result(cache_key)
            if cached is not None:
                return cached

        result = await self._request_token_exchange(pat)
        if cache_key is not None:
            await self._store_cached_result(cache_key, result)
        return result

    def _cache_key(self, pat_fingerprint: str | None) -> str | None:
        if self._redis_client is None or pat_fingerprint is None:
            return None
        return f"knowledge:mcp:token-exchange:{pat_fingerprint}"

    async def _load_cached_result(self, cache_key: str) -> TokenExchangeResult | None:
        assert self._redis_client is not None
        cached = await self._redis_client.get(cache_key)
        if cached is None:
            return None
        try:
            payload = json.loads(cached)
            return TokenExchangeResult.model_validate(payload)
        except (TypeError, ValueError, ValidationError) as exc:
            raise TokenExchangeInfrastructureError(
                "Cached token-exchange result could not be parsed."
            ) from exc

    async def _store_cached_result(self, cache_key: str, result: TokenExchangeResult) -> None:
        assert self._redis_client is not None
        ttl = max(1, min(result.expires_in - 30, self._settings.token_cache_ttl_seconds))
        await self._redis_client.set(
            cache_key,
            json.dumps(result.model_dump(mode="json")),
            ex=ttl,
        )

    async def _request_token_exchange(self, pat: str) -> TokenExchangeResult:
        form_data = {
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
            "grant_type": TOKEN_EXCHANGE_GRANT_TYPE,
            "resource": self._settings.resource,
            "scope": " ".join(self._settings.scopes),
            "subject_token": pat,
            "subject_token_type": LOGTO_PAT_TOKEN_TYPE,
        }
        try:
            if self._http_client is None:
                async with httpx.AsyncClient(timeout=self._settings.http_timeout_seconds) as client:
                    response = await client.post(self._settings.token_url, data=form_data)
            else:
                response = await self._http_client.post(self._settings.token_url, data=form_data)
        except (httpx.HTTPError, OSError) as exc:
            raise TokenExchangeInfrastructureError("Token exchange request failed.") from exc

        if response.status_code in {400, 401, 403}:
            raise TokenExchangeAuthenticationError("Personal Access Token exchange was rejected.")
        if response.status_code < 200 or response.status_code >= 300:
            raise TokenExchangeInfrastructureError("Token exchange service returned an error.")

        try:
            payload = JsonObjectAdapter.validate_python(response.json())
            return TokenExchangeResult.model_validate(payload)
        except ValidationError as exc:
            raise TokenExchangeInfrastructureError(
                "Token exchange response did not match the expected schema."
            ) from exc
