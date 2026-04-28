"""
Abstract: Unit tests for the internal MCP dashboard quota-summary HTTP endpoint.
Out of scope: Live Logto, Redis, and public MCP transport behavior.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from knowledge_mcp.auth.service_token import (
    ServiceTokenAuthenticationError,
    ServiceTokenPrincipal,
)
from knowledge_mcp.internal_quota_summary import QuotaSummaryService, create_quota_summary_endpoint
from knowledge_mcp.quota.store import QuotaSummary, QuotaWindowSnapshot


class FakeServiceTokenVerifier:
    def __init__(self, *, should_reject: bool = False) -> None:
        self.should_reject = should_reject
        self.tokens: list[str] = []

    async def verify_service_token(self, access_token: str) -> ServiceTokenPrincipal:
        self.tokens.append(access_token)
        if self.should_reject:
            raise ServiceTokenAuthenticationError("Missing required token scope.")
        return ServiceTokenPrincipal(
            client_id="web-dashboard-bff",
            scopes=frozenset({"usage:read"}),
        )


class FakeQuotaSummaryService:
    def __init__(self) -> None:
        self.requests: list[str] = []

    async def get_summary(self, *, user_sub: str) -> QuotaSummary:
        self.requests.append(user_sub)
        return QuotaSummary(
            daily=QuotaWindowSnapshot(
                used=37,
                limit=1000,
                remaining=963,
                window_seconds=86_400,
                started_at=datetime(2026, 4, 28, 10, tzinfo=UTC),
                reset_at=datetime(2026, 4, 29, 10, tzinfo=UTC),
            ),
            weekly=QuotaWindowSnapshot(
                used=184,
                limit=5000,
                remaining=4816,
                window_seconds=604_800,
                started_at=datetime(2026, 4, 28, 10, tzinfo=UTC),
                reset_at=datetime(2026, 5, 5, 10, tzinfo=UTC),
            ),
        )


class InactiveQuotaSummaryService:
    async def get_summary(self, *, user_sub: str) -> QuotaSummary:
        return QuotaSummary(
            daily=QuotaWindowSnapshot.inactive(limit=1000, window_seconds=86_400),
            weekly=QuotaWindowSnapshot.inactive(limit=5000, window_seconds=604_800),
        )


def build_client(
    *,
    verifier: FakeServiceTokenVerifier | None = None,
    service: QuotaSummaryService | None = None,
) -> TestClient:
    if service is None:
        service = FakeQuotaSummaryService()
    if verifier is None:
        verifier = FakeServiceTokenVerifier()

    endpoint = create_quota_summary_endpoint(
        service=service,
        service_token_verifier=verifier,
    )
    return TestClient(
        Starlette(
            routes=[
                Route(
                    "/internal/dashboard/quota-summary",
                    endpoint,
                    methods=["POST"],
                )
            ]
        )
    )


def post_summary(
    client: TestClient,
    body: dict[str, Any],
    token: str | None = "service-token",
) -> httpx.Response:
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    return client.post("/internal/dashboard/quota-summary", json=body, headers=headers)


def test_quota_summary_requires_bearer_token() -> None:
    response = post_summary(build_client(), {"userSub": "user_123"}, token=None)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "quota_summary_auth_required"


def test_quota_summary_rejects_invalid_service_token() -> None:
    response = post_summary(
        build_client(verifier=FakeServiceTokenVerifier(should_reject=True)),
        {"userSub": "user_123"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "quota_summary_forbidden"


def test_quota_summary_rejects_invalid_request_body() -> None:
    response = post_summary(build_client(), {"userSub": ""})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "quota_summary_invalid_request"


def test_quota_summary_returns_daily_and_weekly_windows() -> None:
    service = FakeQuotaSummaryService()
    verifier = FakeServiceTokenVerifier()
    response = post_summary(
        build_client(service=service, verifier=verifier),
        {"userSub": "user_123"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "quota": {
            "daily": {
                "used": 37,
                "limit": 1000,
                "remaining": 963,
                "windowSeconds": 86_400,
                "startedAt": "2026-04-28T10:00:00Z",
                "resetAt": "2026-04-29T10:00:00Z",
            },
            "weekly": {
                "used": 184,
                "limit": 5000,
                "remaining": 4816,
                "windowSeconds": 604_800,
                "startedAt": "2026-04-28T10:00:00Z",
                "resetAt": "2026-05-05T10:00:00Z",
            },
        }
    }
    assert verifier.tokens == ["service-token"]
    assert service.requests == ["user_123"]


def test_quota_summary_serializes_inactive_windows_with_null_timestamps() -> None:
    response = post_summary(
        build_client(service=InactiveQuotaSummaryService()),
        {"userSub": "user_123"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "quota": {
            "daily": {
                "used": 0,
                "limit": 1000,
                "remaining": 1000,
                "windowSeconds": 86_400,
                "startedAt": None,
                "resetAt": None,
            },
            "weekly": {
                "used": 0,
                "limit": 5000,
                "remaining": 5000,
                "windowSeconds": 604_800,
                "startedAt": None,
                "resetAt": None,
            },
        }
    }
