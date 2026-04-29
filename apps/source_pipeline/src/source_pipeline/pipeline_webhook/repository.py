"""
Abstract: Persistence accessors for idempotent job-queue webhook events.
Out of scope: HTTP authentication and source-pipeline state advancement.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from source_pipeline.db.models import JobQueueWebhookEvent, JobQueueWebhookWakeup
from source_pipeline.pipeline_webhook.contracts import JobQueueWebhookPayload


class JobQueueWebhookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_event(self, payload: JobQueueWebhookPayload) -> JobQueueWebhookEvent:
        statement = (
            insert(JobQueueWebhookEvent)
            .values(
                event_id=payload.event_id,
                event_type=payload.event_type,
                job_id=payload.job_id,
                queue_name=payload.queue_name,
                submission_id=payload.submission_id,
                terminal_state=payload.terminal_state,
                occurred_at=payload.occurred_at,
                payload=payload.model_dump(mode="json"),
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(JobQueueWebhookEvent)
        )
        record = await self._session.scalar(statement)
        if record is None:
            existing = await self._session.scalar(
                select(JobQueueWebhookEvent)
                .where(JobQueueWebhookEvent.event_id == payload.event_id)
                .limit(1)
            )
            if existing is None:
                raise RuntimeError("Webhook event conflict did not return an existing row.")
            return existing

        wakeup_statement = (
            insert(JobQueueWebhookWakeup)
            .values(event_id=record.event_id)
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        await self._session.execute(wakeup_statement)
        return record

    async def list_pending_events(self, *, limit: int) -> list[JobQueueWebhookEvent]:
        return list(
            await self._session.scalars(
                select(JobQueueWebhookEvent)
                .join(
                    JobQueueWebhookWakeup,
                    JobQueueWebhookWakeup.event_id == JobQueueWebhookEvent.event_id,
                )
                .where(JobQueueWebhookEvent.processed_at.is_(None))
                .order_by(
                    JobQueueWebhookWakeup.id.asc(),
                    JobQueueWebhookEvent.created_at.asc(),
                    JobQueueWebhookEvent.id.asc(),
                )
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )

    async def mark_processed(self, *, event_id: str, processed_at: datetime) -> None:
        record = await self._get_event(event_id)
        record.processed_at = processed_at
        record.last_error = None
        record.updated_at = processed_at
        await self._session.execute(
            delete(JobQueueWebhookWakeup).where(JobQueueWebhookWakeup.event_id == event_id)
        )
        await self._session.flush()

    async def mark_failed(self, *, event_id: str, last_error: str, failed_at: datetime) -> None:
        record = await self._get_event(event_id)
        record.processed_at = None
        record.last_error = last_error
        record.updated_at = failed_at
        await self._session.flush()

    async def _get_event(self, event_id: str) -> JobQueueWebhookEvent:
        record = await self._session.scalar(
            select(JobQueueWebhookEvent)
            .where(JobQueueWebhookEvent.event_id == event_id)
            .limit(1)
            .with_for_update()
        )
        if record is None:
            raise ValueError(f"Job queue webhook event {event_id} does not exist.")
        return record


__all__ = ["JobQueueWebhookEventRepository"]
