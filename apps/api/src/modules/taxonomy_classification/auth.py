"""
Abstract: Taxonomy-classification Logto bearer-token validation for webhook intake.
Out of scope: HTTP route handling and webhook event persistence behavior.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import httpx
import jwt
from jwt import PyJWK
from jwt.exceptions import InvalidKeyError, InvalidTokenError, PyJWKError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, ValidationError

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
JsonObjectAdapter = TypeAdapter(dict[str, object])


class WebhookAuthenticationError(ValueError):
    pass


class WebhookAuthInfrastructureError(RuntimeError):
    pass


class WebhookReceiverAuthSettings(BaseModel):
    issuer: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    discovery_url: str = Field(min_length=1)
    allowed_client_id: str = Field(min_length=1)
    http_timeout_seconds: float = Field(default=5.0, gt=0)


class WebhookPrincipal(BaseModel):
    subject: str = Field(min_length=1)
    client_id: str = Field(min_length=1)


class OidcDiscoveryDocument(BaseModel):
    jwks_uri: str = Field(min_length=1)


class JsonWebKey(BaseModel):
    model_config = ConfigDict(extra="allow")

    kid: NonEmptyString


class JwksDocument(BaseModel):
    keys: list[JsonWebKey]


class DecodedTokenClaims(BaseModel):
    iss: NonEmptyString
    sub: NonEmptyString
    exp: int
    aud: NonEmptyString | list[NonEmptyString]
    client_id: NonEmptyString | None = None
    azp: NonEmptyString | None = None


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


def _matches_resource(audience_claim: str | list[str], configured_resource: str) -> bool:
    if isinstance(audience_claim, str):
        return _normalize_url(audience_claim) == configured_resource
    return any(_normalize_url(audience) == configured_resource for audience in audience_claim)


class WebhookAuthVerifier:
    def __init__(
        self,
        *,
        settings: WebhookReceiverAuthSettings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._issuer = _normalize_url(settings.issuer)
        self._resource = _normalize_url(settings.resource)
        self._discovery_url = settings.discovery_url
        self._allowed_client_id = settings.allowed_client_id
        self._http_timeout_seconds = settings.http_timeout_seconds
        self._http_client = http_client
        self._jwks_by_kid: dict[str, dict[str, object]] | None = None
        self._jwks_uri: str | None = None
        self._lock = asyncio.Lock()

    async def verify_authorization_header(
        self,
        authorization: str | None,
    ) -> WebhookPrincipal:
        if authorization is None or not authorization.lower().startswith("bearer "):
            raise WebhookAuthenticationError("Missing bearer token.")

        token = authorization[7:].strip()
        if not token:
            raise WebhookAuthenticationError("Missing bearer token.")

        try:
            unverified_header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise WebhookAuthenticationError("Invalid bearer token.") from exc

        signing_key = await self._resolve_signing_key(unverified_header.get("kid"))
        if signing_key is None:
            raise WebhookAuthenticationError("Unknown token signing key.")

        try:
            raw_claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[signing_key.algorithm_name],
                options={
                    "require": ["exp", "aud", "iss", "sub"],
                    "verify_aud": False,
                },
            )
            claims = DecodedTokenClaims.model_validate(raw_claims)
        except (InvalidTokenError, ValidationError) as exc:
            raise WebhookAuthenticationError("Invalid bearer token.") from exc

        if _normalize_url(claims.iss) != self._issuer:
            raise WebhookAuthenticationError("Invalid token issuer.")
        if not _matches_resource(claims.aud, self._resource):
            raise WebhookAuthenticationError("Invalid token audience.")

        client_id = claims.client_id or claims.azp or claims.sub
        if client_id != self._allowed_client_id:
            raise WebhookAuthenticationError("Invalid webhook caller identity.")

        return WebhookPrincipal(subject=claims.sub, client_id=client_id)

    async def _resolve_signing_key(self, key_id: object) -> PyJWK | None:
        if not isinstance(key_id, str) or key_id == "":
            return None

        jwks_by_kid = await self._load_jwks_by_kid()
        signing_jwk = jwks_by_kid.get(key_id)
        if signing_jwk is None:
            jwks_by_kid = await self._load_jwks_by_kid(force_refresh=True)
            signing_jwk = jwks_by_kid.get(key_id)
            if signing_jwk is None:
                return None

        try:
            return PyJWK.from_dict(signing_jwk)
        except (InvalidKeyError, PyJWKError) as exc:
            raise WebhookAuthInfrastructureError("JWKS signing key could not be parsed.") from exc

    async def _load_jwks_by_kid(
        self,
        *,
        force_refresh: bool = False,
    ) -> dict[str, dict[str, object]]:
        async with self._lock:
            if self._jwks_by_kid is not None and not force_refresh:
                return self._jwks_by_kid

            jwks_uri = self._jwks_uri
            if jwks_uri is None or force_refresh:
                try:
                    discovery_document = OidcDiscoveryDocument.model_validate(
                        await self._fetch_json(self._discovery_url)
                    )
                except ValidationError as exc:
                    raise WebhookAuthInfrastructureError(
                        "OIDC discovery document does not include jwks_uri."
                    ) from exc
                jwks_uri = discovery_document.jwks_uri
                self._jwks_uri = jwks_uri

            try:
                jwks_document = JwksDocument.model_validate(await self._fetch_json(jwks_uri))
            except ValidationError as exc:
                raise WebhookAuthInfrastructureError("JWKS payload does not include keys.") from exc

            self._jwks_by_kid = {key.kid: key.model_dump(mode="json") for key in jwks_document.keys}
            return self._jwks_by_kid

    async def _fetch_json(self, url: str) -> dict[str, object]:
        try:
            if self._http_client is None:
                async with httpx.AsyncClient(timeout=self._http_timeout_seconds) as client:
                    response = await client.get(url)
            else:
                response = await self._http_client.get(url)
            response.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            raise WebhookAuthInfrastructureError(
                f"Authentication metadata request failed for '{url}'."
            ) from exc

        try:
            return JsonObjectAdapter.validate_python(response.json())
        except ValidationError as exc:
            raise WebhookAuthInfrastructureError(
                f"Authentication metadata response for '{url}' must be a JSON object."
            ) from exc


__all__ = [
    "WebhookAuthInfrastructureError",
    "WebhookAuthVerifier",
    "WebhookAuthenticationError",
    "WebhookPrincipal",
    "WebhookReceiverAuthSettings",
]
