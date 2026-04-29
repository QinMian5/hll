"""
Abstract: Unit tests for ingestion request allocation, enqueue semantics, and logging.
Out of scope: FastAPI request parsing and worker-side processing behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from core.errors import ErrorCode, InfrastructureError
from modules.ingestion.queue import IngestionTask
from modules.ingestion.repo import IngestionRequest, IngestionRequestResolution
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
class _MemoryIngestionRequestRepo:
    records_by_key: dict[str, IngestionRequest]
    created_records: list[IngestionRequest]
    next_id: int = 1
    commit_count: int = 0
    rollback_count: int = 0

    async def get_or_create_request(
        self,
        *,
        idempotency_key: str | None,
        payload_hash: str,
    ) -> IngestionRequestResolution:
        if idempotency_key is not None and idempotency_key in self.records_by_key:
            return IngestionRequestResolution(
                request=self.records_by_key[idempotency_key],
                created=False,
            )

        record = IngestionRequest(
            id=self.next_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )
        self.next_id += 1
        if idempotency_key is not None:
            self.records_by_key[idempotency_key] = record
        self.created_records.append(record)
        return IngestionRequestResolution(request=record, created=True)

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1
        for record in self.created_records:
            if record.idempotency_key is not None:
                self.records_by_key.pop(record.idempotency_key, None)


@dataclass(slots=True)
class _FailingIngestionRequestRepo:
    rollback_count: int = 0

    async def get_or_create_request(
        self,
        *,
        idempotency_key: str | None,
        payload_hash: str,
    ) -> IngestionRequestResolution:
        raise RuntimeError("ingestion request resolution failed")

    async def commit(self) -> None:
        raise AssertionError("commit should not run after lookup failure")

    async def rollback(self) -> None:
        self.rollback_count += 1


@pytest.mark.anyio
async def test_accept_enqueues_message_and_returns_accepted_payload() -> None:
    publisher = _RecorderPublisher(calls=[])
    ingestion_repo = _MemoryIngestionRequestRepo(records_by_key={}, created_records=[])
    service = IngestionService(task_publisher=publisher, ingestion_repo=ingestion_repo)

    response = await service.accept(
        payload=IngestionCreateRequest(title="T", content="C"),
        request_id="req_123",
    )

    assert response.accepted is True
    assert response.ingestion_id == 1
    assert len(publisher.calls) == 1
    assert publisher.calls[0].request_id == "req_123"
    assert publisher.calls[0].title == "T"
    assert publisher.calls[0].content == "C"
    assert publisher.calls[0].ingestion_id == response.ingestion_id
    assert ingestion_repo.created_records == [
        IngestionRequest(
            id=1, idempotency_key=None, payload_hash=ingestion_repo.created_records[0].payload_hash
        )
    ]
    assert ingestion_repo.commit_count == 1
    assert ingestion_repo.rollback_count == 0


@pytest.mark.anyio
async def test_accept_rolls_back_when_enqueue_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ingestion_repo = _MemoryIngestionRequestRepo(records_by_key={}, created_records=[])
    service = IngestionService(
        task_publisher=_FailingPublisher(),
        ingestion_repo=ingestion_repo,
    )
    caplog.set_level(logging.ERROR)

    with pytest.raises(InfrastructureError) as exc_info:
        await service.accept(
            payload=IngestionCreateRequest(title="T", content="C"),
            request_id="req_abc",
        )

    assert exc_info.value.code == ErrorCode.INFRA_QUEUE_UNAVAILABLE
    assert ingestion_repo.commit_count == 0
    assert ingestion_repo.rollback_count == 1
    assert "ingestion.enqueue_failed" in caplog.text
    matching_records = [
        record for record in caplog.records if record.message == "ingestion.enqueue_failed"
    ]
    assert matching_records
    assert matching_records[0].request_id == "req_abc"


@pytest.mark.anyio
async def test_accept_with_new_idempotency_key_persists_and_publishes_once() -> None:
    publisher = _RecorderPublisher(calls=[])
    ingestion_repo = _MemoryIngestionRequestRepo(records_by_key={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        ingestion_repo=ingestion_repo,
    )

    response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_first",
        idempotency_key="source-candidate-1",
    )

    assert response.accepted is True
    assert response.ingestion_id == 1
    assert len(publisher.calls) == 1
    assert publisher.calls[0].ingestion_id == response.ingestion_id
    assert ingestion_repo.created_records == [
        IngestionRequest(
            id=1,
            idempotency_key="source-candidate-1",
            payload_hash=ingestion_repo.created_records[0].payload_hash,
        )
    ]
    assert ingestion_repo.created_records[0].payload_hash
    assert ingestion_repo.commit_count == 1
    assert ingestion_repo.rollback_count == 0


@pytest.mark.anyio
async def test_accept_with_new_idempotency_key_rolls_back_when_publish_fails() -> None:
    ingestion_repo = _MemoryIngestionRequestRepo(records_by_key={}, created_records=[])
    service = IngestionService(
        task_publisher=_FailingPublisher(),
        ingestion_repo=ingestion_repo,
    )

    with pytest.raises(InfrastructureError) as exc_info:
        await service.accept(
            payload=IngestionCreateRequest(title="Title", content="Content"),
            request_id="req_first",
            idempotency_key="source-candidate-1",
        )

    assert exc_info.value.code == ErrorCode.INFRA_QUEUE_UNAVAILABLE
    assert ingestion_repo.records_by_key == {}
    assert ingestion_repo.commit_count == 0
    assert ingestion_repo.rollback_count == 1


@pytest.mark.anyio
async def test_accept_replays_same_key_same_payload_without_publishing() -> None:
    publisher = _RecorderPublisher(calls=[])
    ingestion_repo = _MemoryIngestionRequestRepo(records_by_key={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        ingestion_repo=ingestion_repo,
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
    assert ingestion_repo.commit_count == 1


@pytest.mark.anyio
async def test_accept_rejects_same_key_conflicting_payload_without_publishing() -> None:
    publisher = _RecorderPublisher(calls=[])
    ingestion_repo = _MemoryIngestionRequestRepo(records_by_key={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        ingestion_repo=ingestion_repo,
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
    ingestion_repo = _MemoryIngestionRequestRepo(records_by_key={}, created_records=[])
    service = IngestionService(
        task_publisher=publisher,
        ingestion_repo=ingestion_repo,
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
    assert [first_response.ingestion_id, second_response.ingestion_id] == [1, 2]
    assert [task.request_id for task in publisher.calls] == ["req_first", "req_second"]
    assert [record.idempotency_key for record in ingestion_repo.created_records] == [None, None]
    assert ingestion_repo.commit_count == 2


@pytest.mark.anyio
async def test_accept_does_not_swallow_ingestion_repository_failures() -> None:
    publisher = _RecorderPublisher(calls=[])
    ingestion_repo = _FailingIngestionRequestRepo()
    service = IngestionService(
        task_publisher=publisher,
        ingestion_repo=ingestion_repo,
    )

    with pytest.raises(RuntimeError, match="ingestion request resolution failed"):
        await service.accept(
            payload=IngestionCreateRequest(title="Title", content="Content"),
            request_id="req_first",
            idempotency_key="source-candidate-1",
        )

    assert publisher.calls == []
    assert ingestion_repo.rollback_count == 1
