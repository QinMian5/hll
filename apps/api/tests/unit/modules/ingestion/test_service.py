"""
Abstract: Unit tests for ingestion acceptance service enqueue semantics and logging.
Out of scope: FastAPI request parsing and worker-side processing behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from modules.ingestion.queue import IngestionTask
from modules.ingestion.schema import IngestionCreateRequest
from modules.ingestion.service import IngestionService


@dataclass(slots=True)
class _RecorderPublisher:
    calls: list[IngestionTask]

    def __call__(self, task: IngestionTask) -> None:
        self.calls.append(task)


@dataclass(slots=True)
class _FailingPublisher:
    def __call__(self, task: IngestionTask) -> None:
        raise RuntimeError("broker down")


@pytest.mark.anyio
async def test_accept_enqueues_message_and_returns_accepted_payload() -> None:
    publisher = _RecorderPublisher(calls=[])
    service = IngestionService(task_publisher=publisher)

    response = await service.accept(
        payload=IngestionCreateRequest(title="T", content="C"),
        request_id="req_123",
    )

    assert response.accepted is True
    assert response.ingestion_id.startswith("ing_")
    assert len(publisher.calls) == 1
    assert publisher.calls[0].request_id == "req_123"
    assert publisher.calls[0].title == "T"
    assert publisher.calls[0].content == "C"
    assert publisher.calls[0].ingestion_id == response.ingestion_id


@pytest.mark.anyio
async def test_accept_returns_202_semantics_even_when_enqueue_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = IngestionService(task_publisher=_FailingPublisher())
    caplog.set_level(logging.ERROR)

    response = await service.accept(
        payload=IngestionCreateRequest(title="T", content="C"),
        request_id="req_abc",
    )

    assert response.accepted is True
    assert response.ingestion_id.startswith("ing_")
    assert "ingestion.enqueue_failed" in caplog.text
    matching_records = [
        record for record in caplog.records if record.message == "ingestion.enqueue_failed"
    ]
    assert matching_records
    assert matching_records[0].request_id == "req_abc"
