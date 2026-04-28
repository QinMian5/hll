"""
Abstract: Unit tests for the internal MCP dashboard usage-summary HTTP endpoint.
Out of scope: Live Logto, PostgreSQL, and public MCP transport behavior.
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
from knowledge_mcp.internal_usage_summary import create_usage_summary_endpoint
from knowledge_mcp.usage.summary import UsageSummaryRow

PAT_A = "pat_" + ("a" * 64)


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


class FakeUsageSummaryService:
    def __init__(self) -> None:
        self.requests: list[list[str]] = []

    async def get_summaries(self, pat_fingerprints: list[str]) -> list[UsageSummaryRow]:
        self.requests.append(pat_fingerprints)
        return [
            UsageSummaryRow(
                patFingerprint=PAT_A,
                successfulSearchCount=3,
                last_used_at=datetime(2026, 4, 28, 10, tzinfo=UTC),
            )
        ]


def build_client(
    *,
    verifier: FakeServiceTokenVerifier | None = None,
    service: FakeUsageSummaryService | None = None,
    max_batch_size: int = 100,
) -> TestClient:
    endpoint = create_usage_summary_endpoint(
        service=service or FakeUsageSummaryService(),
        service_token_verifier=verifier or FakeServiceTokenVerifier(),
        max_batch_size=max_batch_size,
    )
    return TestClient(
        Starlette(
            routes=[
                Route(
                    "/internal/dashboard/usage-summary",
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
    return client.post("/internal/dashboard/usage-summary", json=body, headers=headers)


def test_usage_summary_requires_bearer_token() -> None:
    response = post_summary(build_client(), {"patFingerprints": [PAT_A]}, token=None)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "usage_summary_auth_required"


def test_usage_summary_rejects_invalid_service_token() -> None:
    response = post_summary(
        build_client(verifier=FakeServiceTokenVerifier(should_reject=True)),
        {"patFingerprints": [PAT_A]},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "usage_summary_forbidden"


def test_usage_summary_rejects_invalid_fingerprint() -> None:
    response = post_summary(build_client(), {"patFingerprints": ["raw_pat_secret"]})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "usage_summary_invalid_request"


def test_usage_summary_rejects_oversized_batch() -> None:
    response = post_summary(
        build_client(max_batch_size=1),
        {"patFingerprints": [PAT_A, "pat_" + ("b" * 64)]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "usage_summary_invalid_request"


def test_usage_summary_returns_successful_search_counts() -> None:
    service = FakeUsageSummaryService()
    verifier = FakeServiceTokenVerifier()
    response = post_summary(
        build_client(service=service, verifier=verifier),
        {"patFingerprints": [PAT_A]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "summaries": [
            {
                "patFingerprint": PAT_A,
                "successfulSearchCount": 3,
                "lastUsedAt": "2026-04-28T10:00:00Z",
            }
        ]
    }
    assert verifier.tokens == ["service-token"]
    assert service.requests == [[PAT_A]]
