"""
Abstract: Unit tests for Logto access-token validation in the MCP service.
Out of scope: PAT token exchange and MCP transport behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from knowledge_mcp.auth.verifier import (
    AccessTokenVerifier,
    TokenAuthenticationError,
    TokenVerifierSettings,
)


@dataclass(frozen=True)
class SigningKey:
    private_key: rsa.RSAPrivateKey
    jwk: dict[str, object]


def build_signing_key() -> SigningKey:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk["kid"] = "test-key"
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"
    return SigningKey(private_key=private_key, jwk=jwk)


def build_token(
    signing_key: SigningKey,
    *,
    issuer: str = "https://knowledge-logto.example.com/oidc",
    audience: str = "https://knowledge.example.com/mcp",
    subject: str = "user_123",
    scope: str = "search:use other:scope",
    expires_delta: timedelta = timedelta(minutes=5),
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": issuer,
            "sub": subject,
            "aud": audience,
            "exp": int((now + expires_delta).timestamp()),
            "iat": int(now.timestamp()),
            "scope": scope,
        },
        signing_key.private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def build_verifier(signing_key: SigningKey) -> AccessTokenVerifier:
    def handler(request: httpx.Request) -> httpx.Response:
        if (
            str(request.url)
            == "https://knowledge-logto.example.com/oidc/.well-known/openid-configuration"
        ):
            return httpx.Response(
                200,
                json={"jwks_uri": "https://knowledge-logto.example.com/oidc/jwks"},
                request=request,
            )
        if str(request.url) == "https://knowledge-logto.example.com/oidc/jwks":
            return httpx.Response(200, json={"keys": [signing_key.jwk]}, request=request)
        return httpx.Response(404, request=request)

    return AccessTokenVerifier(
        settings=TokenVerifierSettings(
            issuer="https://knowledge-logto.example.com/oidc",
            resource="https://knowledge.example.com/mcp",
            discovery_url="https://knowledge-logto.example.com/oidc/.well-known/openid-configuration",
            required_scopes=("search:use",),
        ),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


@pytest.mark.anyio
async def test_valid_access_token_returns_principal() -> None:
    signing_key = build_signing_key()
    verifier = build_verifier(signing_key)

    principal = await verifier.verify_access_token(
        build_token(signing_key),
        pat_fingerprint="pat_fingerprint",
    )

    assert principal.user_sub == "user_123"
    assert principal.pat_fingerprint == "pat_fingerprint"
    assert principal.scopes == frozenset({"search:use", "other:scope"})


@pytest.mark.anyio
@pytest.mark.parametrize(
    "token_kwargs",
    [
        {"issuer": "https://other-logto.example.com/oidc"},
        {"audience": "https://wrong-resource.example.com"},
        {"scope": "other:scope"},
        {"expires_delta": timedelta(minutes=-5)},
    ],
)
async def test_invalid_issuer_audience_scope_or_expiry_is_rejected(
    token_kwargs: dict[str, object],
) -> None:
    signing_key = build_signing_key()
    verifier = build_verifier(signing_key)

    with pytest.raises(TokenAuthenticationError):
        await verifier.verify_access_token(
            build_token(signing_key, **token_kwargs),
            pat_fingerprint="pat_fingerprint",
        )
