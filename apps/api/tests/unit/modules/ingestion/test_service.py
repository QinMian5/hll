"""
Abstract: Unit tests for ingestion acceptance service enqueue semantics and logging.
Out of scope: FastAPI request parsing and worker-side processing behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from modules.ingestion.schema import IngestionCreateRequest
from modules.ingestion.service import IngestionService


@dataclass(slots=True)
class _RecorderSender:
    calls: list[tuple[object, ...]]

    def send(self, *args: object) -> None:
        self.calls.append(args)


@dataclass(slots=True)
class _FailingSender:
    def send(self, *args: object) -> None:
        raise RuntimeError("broker down")


@pytest.mark.anyio
async def test_accept_enqueues_message_and_returns_accepted_payload() -> None:
    sender = _RecorderSender(calls=[])
    service = IngestionService(enqueue_sender=sender)

    response = await service.accept(
        payload=IngestionCreateRequest(title="T", content="C"),
        request_id="req_123",
    )

    assert response.accepted is True
    assert response.ingestion_id.startswith("ing_")
    assert len(sender.calls) == 1
    assert sender.calls[0][1] == "req_123"
    assert sender.calls[0][2] == "T"
    assert sender.calls[0][3] == "C"


@pytest.mark.anyio
async def test_accept_returns_202_semantics_even_when_enqueue_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = IngestionService(enqueue_sender=_FailingSender())
    caplog.set_level(logging.ERROR)

    response = await service.accept(
        payload=IngestionCreateRequest(title="T", content="C"),
        request_id="req_abc",
    )

    assert response.accepted is True
    assert response.ingestion_id.startswith("ing_")
    assert "ingestion.enqueue_failed" in caplog.text
    matching_records = [
        record
        for record in caplog.records
        if record.message == "ingestion.enqueue_failed"
    ]
    assert matching_records
    assert matching_records[0].request_id == "req_abc"
