"""
Abstract: Unit tests for the thin job-queue HTTP client.
Out of scope: Orchestrator state transitions and database persistence.
"""

from __future__ import annotations

import httpx
import pytest

from source_pipeline.pipeline_runtime.job_queue_client import JobQueueClient
from source_pipeline.pipeline_runtime.job_queue_token import ClientCredentialsTokenProvider


class StaticTokenProvider:
    async def get_access_token(self) -> str:
        return "oauth-token"

    async def aclose(self) -> None:
        return None


@pytest.mark.anyio
async def test_create_job_posts_expected_payload_and_returns_job_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://queue/producer/jobs"
        assert request.headers["Authorization"] == "Bearer oauth-token"
        assert request.read() == (
            b'{"queue_name":"page_to_card","priority":"normal",'
            b'"instruction":"extract cards","output_schema":{"type":"object"},'
            b'"payload":{"source_ref":"page-1"},"metadata":{"run_id":1}}'
        )
        return httpx.Response(201, json={"job_id": 12})

    client = JobQueueClient(
        base_url="http://queue",
        token_provider=StaticTokenProvider(),
        transport=httpx.MockTransport(handler),
    )

    job_id = await client.create_job(
        queue_name="page_to_card",
        priority="normal",
        instruction="extract cards",
        output_schema={"type": "object"},
        payload={"source_ref": "page-1"},
        metadata={"run_id": 1},
    )

    assert job_id == 12


@pytest.mark.anyio
async def test_get_result_returns_not_ready_and_terminal_state() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            202,
            json={"job_id": 7, "state": "FAILED", "result_ready": False},
        )
    )
    client = JobQueueClient(
        base_url="http://queue",
        token_provider=StaticTokenProvider(),
        transport=transport,
    )

    result = await client.get_result(job_id=7)

    assert result.kind == "not_ready"
    assert result.state == "FAILED"


@pytest.mark.anyio
async def test_get_result_returns_accepted_payload() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "job_id": 7,
                "submission_id": 3,
                "received_at": "2026-04-20T22:55:00Z",
                "result_payload": {"cards": []},
            },
        )
    )
    client = JobQueueClient(
        base_url="http://queue",
        token_provider=StaticTokenProvider(),
        transport=transport,
    )

    result = await client.get_result(job_id=7)

    assert result.kind == "accepted"
    assert result.result_payload == {"cards": []}


@pytest.mark.anyio
async def test_client_credentials_token_provider_posts_oauth_request_and_caches_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert str(request.url) == "http://logto/oidc/token"
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert request.read().decode() == (
            "grant_type=client_credentials&"
            "client_id=client-id&"
            "client_secret=client-secret&"
            "resource=https%3A%2F%2Fjq-mcp.orbitalis.org&"
            "scope=jobs%3Acreate+results%3Aread"
        )
        return httpx.Response(
            200,
            json={
                "access_token": "logto-token",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

    provider = ClientCredentialsTokenProvider(
        token_url="http://logto/oidc/token",
        client_id="client-id",
        client_secret="client-secret",
        resource="https://jq-mcp.orbitalis.org",
        scope="jobs:create results:read",
        transport=httpx.MockTransport(handler),
    )

    first_token = await provider.get_access_token()
    second_token = await provider.get_access_token()

    assert first_token == "logto-token"
    assert second_token == "logto-token"
    assert len(requests) == 1
