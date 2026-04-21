"""
Abstract: Unit tests for the thin job-queue HTTP client.
Out of scope: Orchestrator state transitions and database persistence.
"""

from __future__ import annotations

import httpx
import pytest

from source_pipeline.pipeline_runtime.job_queue_client import JobQueueClient


@pytest.mark.anyio
async def test_create_job_posts_expected_payload_and_returns_job_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "http://queue/producer/jobs"
        assert request.headers["Authorization"] == "Bearer producer-token"
        assert request.read() == (
            b'{"queue_name":"source_pipeline.page_to_card","priority":"normal",'
            b'"instruction":"extract cards","output_schema":{"type":"array"},'
            b'"payload":{"source_ref":"page-1"},"metadata":{"run_id":1}}'
        )
        return httpx.Response(201, json={"job_id": 12})

    client = JobQueueClient(
        base_url="http://queue",
        producer_token="producer-token",
        results_reader_token="results-token",
        transport=httpx.MockTransport(handler),
    )

    job_id = await client.create_job(
        queue_name="source_pipeline.page_to_card",
        priority="normal",
        instruction="extract cards",
        output_schema={"type": "array"},
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
        producer_token="producer-token",
        results_reader_token="results-token",
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
        producer_token="producer-token",
        results_reader_token="results-token",
        transport=transport,
    )

    result = await client.get_result(job_id=7)

    assert result.kind == "accepted"
    assert result.result_payload == {"cards": []}
