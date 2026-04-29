"""
Abstract: Integration tests for source-pipeline webhook event persistence.
Out of scope: HTTP receiver authentication and runtime orchestration behavior.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from source_pipeline.db.models import JobQueueWebhookEvent, JobQueueWebhookWakeup
from source_pipeline.pipeline_webhook.contracts import JobQueueWebhookPayload
from source_pipeline.pipeline_webhook.repository import JobQueueWebhookEventRepository

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


def build_payload(
    *,
    event_id: str = "evt-1",
    event_type: str = "result.accepted",
    job_id: int = 42,
) -> JobQueueWebhookPayload:
    return JobQueueWebhookPayload.model_validate(
        {
            "event_id": event_id,
            "event_type": event_type,
            "job_id": job_id,
            "queue_name": "page_to_card",
            "occurred_at": datetime(2026, 4, 25, 15, 1, tzinfo=UTC),
            "submission_id": 142 if event_type == "result.accepted" else None,
            "terminal_state": "DEAD_LETTER" if event_type == "job.terminal_non_accepted" else None,
        }
    )


async def count_wakeups(db_session: AsyncSession, *, event_id: str) -> int:
    count = await db_session.scalar(
        select(func.count())
        .select_from(JobQueueWebhookWakeup)
        .where(JobQueueWebhookWakeup.event_id == event_id)
    )
    return int(count or 0)


async def test_insert_event_persists_raw_payload_and_emits_one_wakeup(
    db_session: AsyncSession,
) -> None:
    repository = JobQueueWebhookEventRepository(db_session)
    payload = build_payload(event_id="evt-insert")

    event = await repository.record_event(payload)
    await db_session.flush()

    persisted = await db_session.get(JobQueueWebhookEvent, event.id)

    assert persisted is not None
    assert persisted.event_id == "evt-insert"
    assert persisted.event_type == "result.accepted"
    assert persisted.job_id == 42
    assert persisted.queue_name == "page_to_card"
    assert persisted.submission_id == 142
    assert persisted.terminal_state is None
    assert persisted.occurred_at == datetime(2026, 4, 25, 15, 1, tzinfo=UTC)
    assert persisted.payload == payload.model_dump(mode="json")
    assert persisted.processed_at is None
    assert await count_wakeups(db_session, event_id="evt-insert") == 1


async def test_duplicate_event_id_returns_existing_row_without_second_wakeup(
    db_session: AsyncSession,
) -> None:
    repository = JobQueueWebhookEventRepository(db_session)
    payload = build_payload(event_id="evt-duplicate")
    first = await repository.record_event(payload)
    second = await repository.record_event(payload)
    await db_session.flush()

    assert second.id == first.id
    assert await count_wakeups(db_session, event_id="evt-duplicate") == 1


async def test_concurrent_duplicate_event_id_returns_existing_row_without_second_wakeup(
    db_engine: AsyncEngine,
) -> None:
    event_id = f"evt-concurrent-{uuid4().hex}"
    payload = build_payload(event_id=event_id)
    first_flushed = asyncio.Event()
    release_first_commit = asyncio.Event()

    async def record_first_and_hold_commit() -> int:
        async with (
            AsyncSession(db_engine, expire_on_commit=False) as session,
            session.begin(),
        ):
            event = await JobQueueWebhookEventRepository(session).record_event(payload)
            first_flushed.set()
            await release_first_commit.wait()
            return event.id

    async def record_duplicate() -> int:
        await first_flushed.wait()
        async with (
            AsyncSession(db_engine, expire_on_commit=False) as session,
            session.begin(),
        ):
            event = await JobQueueWebhookEventRepository(session).record_event(payload)
            return event.id

    try:
        first_task = asyncio.create_task(record_first_and_hold_commit())
        await first_flushed.wait()
        second_task = asyncio.create_task(record_duplicate())
        await asyncio.sleep(0.1)
        release_first_commit.set()

        first_id, second_id = await asyncio.gather(first_task, second_task)

        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            assert first_id == second_id
            assert await count_wakeups(session, event_id=event_id) == 1
    finally:
        release_first_commit.set()
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            await session.execute(
                delete(JobQueueWebhookWakeup).where(JobQueueWebhookWakeup.event_id == event_id)
            )
            await session.execute(
                delete(JobQueueWebhookEvent).where(JobQueueWebhookEvent.event_id == event_id)
            )
            await session.commit()


async def test_payload_contract_rejects_result_payload_and_lease_token() -> None:
    with pytest.raises(ValueError, match="result_payload"):
        JobQueueWebhookPayload.model_validate(
            {
                "event_id": "evt-sensitive",
                "event_type": "result.accepted",
                "job_id": 42,
                "queue_name": "page_to_card",
                "occurred_at": datetime(2026, 4, 25, 15, 1, tzinfo=UTC),
                "submission_id": 142,
                "result_payload": {"cards": []},
                "lease_token": "must-not-arrive",
            }
        )


async def test_pending_events_list_in_created_order(db_session: AsyncSession) -> None:
    repository = JobQueueWebhookEventRepository(db_session)
    expected_event_ids = ["evt-order-1", "evt-order-2", "evt-order-terminal"]
    await repository.record_event(build_payload(event_id=expected_event_ids[0], job_id=41))
    await repository.record_event(build_payload(event_id=expected_event_ids[1], job_id=42))
    await repository.record_event(
        build_payload(
            event_id=expected_event_ids[2],
            event_type="job.terminal_non_accepted",
            job_id=43,
        )
    )
    await db_session.flush()

    pending = await repository.list_pending_events(limit=10)

    assert [
        event.event_id for event in pending if event.event_id in expected_event_ids
    ] == expected_event_ids


async def test_processing_success_marks_processed_at(db_session: AsyncSession) -> None:
    repository = JobQueueWebhookEventRepository(db_session)
    event = await repository.record_event(build_payload(event_id="evt-success"))
    processed_at = datetime(2026, 4, 25, 15, 5, tzinfo=UTC)

    await repository.mark_processed(event_id=event.event_id, processed_at=processed_at)
    await db_session.flush()
    pending = await repository.list_pending_events(limit=10)

    assert event.processed_at == processed_at
    assert event.last_error is None
    assert event.event_id not in {item.event_id for item in pending}
    assert await count_wakeups(db_session, event_id="evt-success") == 0


async def test_processing_failure_keeps_event_pending_with_error(
    db_session: AsyncSession,
) -> None:
    repository = JobQueueWebhookEventRepository(db_session)
    event = await repository.record_event(build_payload(event_id="evt-failure"))

    await repository.mark_failed(
        event_id=event.event_id,
        last_error="result surface unavailable",
        failed_at=datetime(2026, 4, 25, 15, 5, tzinfo=UTC),
    )
    await db_session.flush()
    pending = await repository.list_pending_events(limit=10)

    assert event.processed_at is None
    assert event.last_error == "result surface unavailable"
    assert event.event_id in {item.event_id for item in pending}
    assert await count_wakeups(db_session, event_id="evt-failure") == 1
