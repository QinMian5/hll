"""
Abstract: Unit tests for source-pipeline webhook bearer-token validation.
Out of scope: HTTP receiver routing and event persistence behavior.
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

from source_pipeline.pipeline_webhook.auth import (
    WebhookAuthenticationError,
    WebhookAuthVerifier,
    WebhookReceiverAuthSettings,
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
    audience: str = "https://knowledge.example.com/source-pipeline-webhooks",
    client_id: str = "job-queue-webhook-delivery",
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": issuer,
            "sub": client_id,
            "aud": audience,
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "client_id": client_id,
        },
        signing_key.private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def build_verifier(signing_key: SigningKey) -> WebhookAuthVerifier:
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

    return WebhookAuthVerifier(
        settings=WebhookReceiverAuthSettings(
            issuer="https://knowledge-logto.example.com/oidc",
            resource="https://knowledge.example.com/source-pipeline-webhooks",
            discovery_url="https://knowledge-logto.example.com/oidc/.well-known/openid-configuration",
            allowed_client_id="job-queue-webhook-delivery",
        ),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


@pytest.mark.anyio
async def test_valid_logto_m2m_token_returns_principal() -> None:
    signing_key = build_signing_key()
    verifier = build_verifier(signing_key)

    principal = await verifier.verify_authorization_header(f"Bearer {build_token(signing_key)}")

    assert principal.client_id == "job-queue-webhook-delivery"
    assert principal.subject == "job-queue-webhook-delivery"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "token_kwargs",
    [
        {"issuer": "https://other-logto.example.com/oidc"},
        {"audience": "https://wrong-resource.example.com"},
        {"client_id": "other-client"},
    ],
)
async def test_wrong_issuer_audience_or_client_identity_is_rejected(
    token_kwargs: dict[str, str],
) -> None:
    signing_key = build_signing_key()
    verifier = build_verifier(signing_key)

    with pytest.raises(WebhookAuthenticationError):
        await verifier.verify_authorization_header(
            f"Bearer {build_token(signing_key, **token_kwargs)}"
        )


@pytest.mark.anyio
async def test_missing_bearer_token_is_rejected() -> None:
    verifier = build_verifier(build_signing_key())

    with pytest.raises(WebhookAuthenticationError):
        await verifier.verify_authorization_header(None)
