"""
Abstract: Logto access-token verification for the public MCP service.
Out of scope: Personal Access Token exchange and MCP tool orchestration.
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


class TokenAuthenticationError(ValueError):
    pass


class TokenVerifierInfrastructureError(RuntimeError):
    pass


class TokenVerifierSettings(BaseModel):
    issuer: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    discovery_url: str = Field(min_length=1)
    required_scopes: tuple[str, ...] = Field(min_length=1)
    http_timeout_seconds: float = Field(default=5.0, gt=0)


class AuthenticatedPrincipal(BaseModel):
    user_sub: str = Field(min_length=1)
    scopes: frozenset[str]
    pat_fingerprint: str = Field(min_length=1)


class OidcDiscoveryDocument(BaseModel):
    jwks_uri: str = Field(min_length=1)


class JsonWebKey(BaseModel):
    model_config = ConfigDict(extra="allow")

    kid: NonEmptyString


class JwksDocument(BaseModel):
    keys: list[JsonWebKey]


class DecodedAccessTokenClaims(BaseModel):
    iss: NonEmptyString
    sub: NonEmptyString
    exp: int
    aud: NonEmptyString | list[NonEmptyString]
    scope: str = ""


def _normalize_url(value: str) -> str:
    return value.rstrip("/")


def _matches_resource(audience_claim: str | list[str], configured_resource: str) -> bool:
    if isinstance(audience_claim, str):
        return _normalize_url(audience_claim) == configured_resource
    return any(_normalize_url(audience) == configured_resource for audience in audience_claim)


def _parse_scope(scope: str) -> frozenset[str]:
    return frozenset(part for part in scope.split() if part)


class AccessTokenVerifier:
    def __init__(
        self,
        *,
        settings: TokenVerifierSettings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._issuer = _normalize_url(settings.issuer)
        self._resource = _normalize_url(settings.resource)
        self._discovery_url = settings.discovery_url
        self._required_scopes = frozenset(settings.required_scopes)
        self._http_timeout_seconds = settings.http_timeout_seconds
        self._http_client = http_client
        self._jwks_by_kid: dict[str, dict[str, object]] | None = None
        self._jwks_uri: str | None = None
        self._lock = asyncio.Lock()

    async def verify_access_token(
        self,
        access_token: str,
        *,
        pat_fingerprint: str,
    ) -> AuthenticatedPrincipal:
        try:
            unverified_header = jwt.get_unverified_header(access_token)
        except InvalidTokenError as exc:
            raise TokenAuthenticationError("Invalid access token.") from exc

        signing_key = await self._resolve_signing_key(unverified_header.get("kid"))
        if signing_key is None:
            raise TokenAuthenticationError("Unknown token signing key.")

        try:
            raw_claims = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=[signing_key.algorithm_name],
                options={
                    "require": ["exp", "aud", "iss", "sub"],
                    "verify_aud": False,
                },
            )
            claims = DecodedAccessTokenClaims.model_validate(raw_claims)
        except (InvalidTokenError, ValidationError) as exc:
            raise TokenAuthenticationError("Invalid access token.") from exc

        if _normalize_url(claims.iss) != self._issuer:
            raise TokenAuthenticationError("Invalid token issuer.")
        if not _matches_resource(claims.aud, self._resource):
            raise TokenAuthenticationError("Invalid token audience.")

        scopes = _parse_scope(claims.scope)
        if not self._required_scopes.issubset(scopes):
            raise TokenAuthenticationError("Missing required token scope.")

        return AuthenticatedPrincipal(
            user_sub=claims.sub,
            scopes=scopes,
            pat_fingerprint=pat_fingerprint,
        )

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
            raise TokenVerifierInfrastructureError("JWKS signing key could not be parsed.") from exc

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
                    raise TokenVerifierInfrastructureError(
                        "OIDC discovery document does not include jwks_uri."
                    ) from exc
                jwks_uri = discovery_document.jwks_uri
                self._jwks_uri = jwks_uri

            try:
                jwks_document = JwksDocument.model_validate(await self._fetch_json(jwks_uri))
            except ValidationError as exc:
                raise TokenVerifierInfrastructureError(
                    "JWKS payload does not include keys."
                ) from exc

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
            raise TokenVerifierInfrastructureError(
                f"Authentication metadata request failed for '{url}'."
            ) from exc

        try:
            return JsonObjectAdapter.validate_python(response.json())
        except ValidationError as exc:
            raise TokenVerifierInfrastructureError(
                f"Authentication metadata response for '{url}' must be a JSON object."
            ) from exc
