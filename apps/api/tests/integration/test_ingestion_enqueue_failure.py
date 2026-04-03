"""
Abstract: Integration test for ingestion HTTP semantics when enqueue fails internally.
Out of scope: Redis broker availability checks and worker execution behavior.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from httpx import AsyncClient

from entrypoints.api import providers as api_providers
from modules.ingestion.queue import IngestionTask
from modules.ingestion.service import IngestionService

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


@dataclass(slots=True)
class _FailingPublisher:
    def __call__(self, task: IngestionTask) -> None:
        raise RuntimeError("queue unavailable")


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {
        api_providers.get_ingestion_service: lambda: IngestionService(
            task_publisher=_FailingPublisher()
        )
    }


@pytest.mark.integration
@pytest.mark.anyio
async def test_valid_ingestion_payload_returns_202_even_if_enqueue_fails(
    async_client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)
    response = await async_client.post(
        "/ingestions/cards",
        headers={"X-Request-ID": "req_integration"},
        json={"title": "Title", "content": "Content"},
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True
    assert response.json()["ingestion_id"].startswith("ing_")
    matching_records = [
        record
        for record in caplog.records
        if record.message == "ingestion.enqueue_failed"
    ]
    assert matching_records
    assert matching_records[0].request_id == "req_integration"
