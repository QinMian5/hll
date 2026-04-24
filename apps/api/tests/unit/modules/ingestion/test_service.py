"""
Abstract: Unit tests for ingestion acceptance service enqueue semantics and logging.
Out of scope: FastAPI request parsing and worker-side processing behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from modules.ingestion.queue import IngestionTask
from modules.ingestion.repo import IngestionIdempotencyRecord
from modules.ingestion.schema import IngestionCreateRequest
from modules.ingestion.service import IngestionIdempotencyConflictError, IngestionService


@dataclass(slots=True)
class _RecorderPublisher:
    calls: list[IngestionTask]

    def __call__(self, task: IngestionTask) -> None:
        self.calls.append(task)


@dataclass(slots=True)
class _FailingPublisher:
    def __call__(self, task: IngestionTask) -> None:
        raise RuntimeError("broker down")


@dataclass(slots=True)
class _MemoryIdempotencyRepo:
    records: dict[str, IngestionIdempotencyRecord]
    created_records: list[IngestionIdempotencyRecord]
    commit_count: int = 0
    rollback_count: int = 0

    async def get_by_key(self, *, idempotency_key: str) -> IngestionIdempotencyRecord | None:
        return self.records.get(idempotency_key)

    async def create_record(
        self,
        *,
        idempotency_key: str,
        payload_hash: str,
        ingestion_id: str,
    ) -> IngestionIdempotencyRecord:
        record = IngestionIdempotencyRecord(
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            ingestion_id=ingestion_id,
        )
        self.records[idempotency_key] = record
        self.created_records.append(record)
        return record

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1
        for record in self.created_records:
            self.records.pop(record.idempotency_key, None)


class _FailingIdempotencyRepo:
    async def get_by_key(self, *, idempotency_key: str) -> IngestionIdempotencyRecord | None:
        raise RuntimeError(f"idempotency lookup failed for {idempotency_key}")

    async def create_record(
        self,
        *,
        idempotency_key: str,
        payload_hash: str,
        ingestion_id: str,
    ) -> IngestionIdempotencyRecord:
        raise AssertionError("create_record should not run after lookup failure")

    async def commit(self) -> None:
        raise AssertionError("commit should not run after lookup failure")

    async def rollback(self) -> None:
        raise AssertionError("rollback should not run after lookup failure")


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


@pytest.mark.anyio
async def test_accept_with_new_idempotency_key_persists_and_publishes_once() -> None:
    publisher = _RecorderPublisher(calls=[])
    idempotency_repo = _MemoryIdempotencyRepo(records={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        idempotency_repo=idempotency_repo,
    )

    response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_first",
        idempotency_key="source-candidate-1",
    )

    assert response.accepted is True
    assert response.ingestion_id.startswith("ing_")
    assert len(publisher.calls) == 1
    assert publisher.calls[0].ingestion_id == response.ingestion_id
    assert idempotency_repo.created_records == [
        IngestionIdempotencyRecord(
            idempotency_key="source-candidate-1",
            payload_hash=idempotency_repo.created_records[0].payload_hash,
            ingestion_id=response.ingestion_id,
        )
    ]
    assert idempotency_repo.created_records[0].payload_hash
    assert idempotency_repo.commit_count == 1
    assert idempotency_repo.rollback_count == 0


@pytest.mark.anyio
async def test_accept_with_new_idempotency_key_rolls_back_when_publish_fails() -> None:
    idempotency_repo = _MemoryIdempotencyRepo(records={}, created_records=[])
    service = IngestionService(
        task_publisher=_FailingPublisher(),
        idempotency_repo=idempotency_repo,
    )

    with pytest.raises(RuntimeError, match="broker down"):
        await service.accept(
            payload=IngestionCreateRequest(title="Title", content="Content"),
            request_id="req_first",
            idempotency_key="source-candidate-1",
        )

    assert idempotency_repo.records == {}
    assert idempotency_repo.commit_count == 0
    assert idempotency_repo.rollback_count == 1


@pytest.mark.anyio
async def test_accept_replays_same_key_same_payload_without_publishing() -> None:
    publisher = _RecorderPublisher(calls=[])
    idempotency_repo = _MemoryIdempotencyRepo(records={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        idempotency_repo=idempotency_repo,
    )
    first_response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_first",
        idempotency_key="source-candidate-1",
    )

    replay_response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_replay",
        idempotency_key="source-candidate-1",
    )

    assert replay_response == first_response
    assert len(publisher.calls) == 1
    assert publisher.calls[0].request_id == "req_first"
    assert idempotency_repo.commit_count == 1


@pytest.mark.anyio
async def test_accept_rejects_same_key_conflicting_payload_without_publishing() -> None:
    publisher = _RecorderPublisher(calls=[])
    idempotency_repo = _MemoryIdempotencyRepo(records={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        idempotency_repo=idempotency_repo,
    )
    await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_first",
        idempotency_key="source-candidate-1",
    )

    with pytest.raises(IngestionIdempotencyConflictError):
        await service.accept(
            payload=IngestionCreateRequest(title="Different", content="Content"),
            request_id="req_conflict",
            idempotency_key="source-candidate-1",
        )

    assert len(publisher.calls) == 1
    assert publisher.calls[0].request_id == "req_first"


@pytest.mark.anyio
async def test_accept_without_non_empty_idempotency_key_keeps_independent_publish_behavior() -> (
    None
):
    publisher = _RecorderPublisher(calls=[])
    idempotency_repo = _MemoryIdempotencyRepo(records={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        idempotency_repo=idempotency_repo,
    )

    first_response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_first",
    )
    second_response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_second",
        idempotency_key="  ",
    )

    assert first_response != second_response
    assert [task.request_id for task in publisher.calls] == ["req_first", "req_second"]
    assert idempotency_repo.created_records == []
    assert idempotency_repo.commit_count == 0


@pytest.mark.anyio
async def test_accept_does_not_swallow_idempotency_repository_failures() -> None:
    publisher = _RecorderPublisher(calls=[])
    service = IngestionService(
        task_publisher=publisher,
        idempotency_repo=_FailingIdempotencyRepo(),
    )

    with pytest.raises(RuntimeError, match="idempotency lookup failed"):
        await service.accept(
            payload=IngestionCreateRequest(title="Title", content="Content"),
            request_id="req_first",
            idempotency_key="source-candidate-1",
        )

    assert publisher.calls == []
