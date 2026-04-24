"""
Abstract: Integration tests for persisted ingestion idempotency semantics.
Out of scope: HTTP header parsing and worker-side materialization behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.ingestion.queue import IngestionTask
from modules.ingestion.repo import IngestionIdempotencyRepo
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


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_idempotent_accept_stores_record_and_replay_does_not_republish(
    db_session: AsyncSession,
) -> None:
    publisher = _RecorderPublisher(calls=[])
    service = IngestionService(
        task_publisher=publisher,
        idempotency_repo=IngestionIdempotencyRepo(session=db_session),
    )

    first_response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_first",
        idempotency_key="source-candidate-1",
    )

    stored_record = await IngestionIdempotencyRepo(session=db_session).get_by_key(
        idempotency_key="source-candidate-1"
    )
    assert stored_record is not None
    assert stored_record.ingestion_id == first_response.ingestion_id
    assert stored_record.payload_hash

    replay_response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_replay",
        idempotency_key="source-candidate-1",
    )

    assert replay_response == first_response
    assert len(publisher.calls) == 1
    assert publisher.calls[0].request_id == "req_first"


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_idempotent_accept_publish_failure_rolls_back_and_retry_publishes_once(
    db_session: AsyncSession,
) -> None:
    failing_service = IngestionService(
        task_publisher=_FailingPublisher(),
        idempotency_repo=IngestionIdempotencyRepo(session=db_session),
    )

    with pytest.raises(RuntimeError, match="broker down"):
        await failing_service.accept(
            payload=IngestionCreateRequest(title="Title", content="Content"),
            request_id="req_publish_failure",
            idempotency_key="source-candidate-publish-retry",
        )

    rolled_back_record = await IngestionIdempotencyRepo(session=db_session).get_by_key(
        idempotency_key="source-candidate-publish-retry"
    )
    assert rolled_back_record is None

    retry_publisher = _RecorderPublisher(calls=[])
    retry_service = IngestionService(
        task_publisher=retry_publisher,
        idempotency_repo=IngestionIdempotencyRepo(session=db_session),
    )
    retry_response = await retry_service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_retry",
        idempotency_key="source-candidate-publish-retry",
    )

    stored_record = await IngestionIdempotencyRepo(session=db_session).get_by_key(
        idempotency_key="source-candidate-publish-retry"
    )
    assert stored_record is not None
    assert stored_record.ingestion_id == retry_response.ingestion_id
    assert len(retry_publisher.calls) == 1
    assert retry_publisher.calls[0].request_id == "req_retry"


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_idempotent_accept_rejects_conflicting_payload(
    db_session: AsyncSession,
) -> None:
    publisher = _RecorderPublisher(calls=[])
    service = IngestionService(
        task_publisher=publisher,
        idempotency_repo=IngestionIdempotencyRepo(session=db_session),
    )
    first_response = await service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_first",
        idempotency_key="source-candidate-2",
    )

    with pytest.raises(IngestionIdempotencyConflictError):
        await service.accept(
            payload=IngestionCreateRequest(title="Different", content="Content"),
            request_id="req_conflict",
            idempotency_key="source-candidate-2",
        )

    assert len(publisher.calls) == 1
    stored_record = await IngestionIdempotencyRepo(session=db_session).get_by_key(
        idempotency_key="source-candidate-2"
    )
    assert stored_record is not None
    assert stored_record.ingestion_id == first_response.ingestion_id


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_replay_after_lost_response_converges_on_original_ingestion_id(
    db_session: AsyncSession,
) -> None:
    first_publisher = _RecorderPublisher(calls=[])
    first_service = IngestionService(
        task_publisher=first_publisher,
        idempotency_repo=IngestionIdempotencyRepo(session=db_session),
    )
    first_response = await first_service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_before_connection_loss",
        idempotency_key="source-candidate-3",
    )

    replay_publisher = _RecorderPublisher(calls=[])
    replay_service = IngestionService(
        task_publisher=replay_publisher,
        idempotency_repo=IngestionIdempotencyRepo(session=db_session),
    )
    replay_response = await replay_service.accept(
        payload=IngestionCreateRequest(title="Title", content="Content"),
        request_id="req_after_connection_loss",
        idempotency_key="source-candidate-3",
    )

    assert replay_response == first_response
    assert len(first_publisher.calls) == 1
    assert replay_publisher.calls == []
