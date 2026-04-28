"""
Abstract: Unit tests for Logto PAT token exchange.
Out of scope: Access-token JWT validation and MCP tool execution.
"""

from __future__ import annotations

import httpx
import pytest

from knowledge_mcp.auth.token_exchange import (
    TokenExchangeAuthenticationError,
    TokenExchangeClient,
    TokenExchangeInfrastructureError,
    TokenExchangeSettings,
)


def _settings() -> TokenExchangeSettings:
    return TokenExchangeSettings(
        token_url="https://logto.example.com/oidc/token",
        client_id="mcp-token-exchange",
        client_secret="client-secret",
        resource="https://knowledge.example.com/mcp",
        scopes=("search:execute",),
        http_timeout_seconds=5.0,
    )


@pytest.mark.anyio
async def test_exchange_pat_sends_logto_token_exchange_request() -> None:
    seen_form: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://logto.example.com/oidc/token"
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        seen_form.update(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(
            200,
            json={
                "access_token": "access-token",
                "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "search:execute",
            },
            request=request,
        )

    client = TokenExchangeClient(
        settings=_settings(),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    result = await client.exchange_pat("pat_secret_value")

    assert result.access_token == "access-token"
    assert result.expires_in == 3600
    assert seen_form == {
        "client_id": "mcp-token-exchange",
        "client_secret": "client-secret",
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "resource": "https://knowledge.example.com/mcp",
        "scope": "search:execute",
        "subject_token": "pat_secret_value",
        "subject_token_type": "urn:logto:token-type:personal_access_token",
    }


@pytest.mark.anyio
async def test_logto_unauthorized_response_maps_to_authentication_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_grant"}, request=request)

    client = TokenExchangeClient(
        settings=_settings(),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TokenExchangeAuthenticationError) as exc_info:
        await client.exchange_pat("pat_secret_value")

    assert "pat_secret_value" not in str(exc_info.value)


@pytest.mark.anyio
async def test_logto_timeout_maps_to_infrastructure_error_without_pat_leak() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout while reading pat_secret_value")

    client = TokenExchangeClient(
        settings=_settings(),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(TokenExchangeInfrastructureError) as exc_info:
        await client.exchange_pat("pat_secret_value")

    assert "pat_secret_value" not in str(exc_info.value)
