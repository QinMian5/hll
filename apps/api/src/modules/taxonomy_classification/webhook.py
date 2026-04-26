"""
Abstract: Taxonomy-classification webhook payload and idempotent event persistence.
Out of scope: Bearer-token verification and taxonomy assignment movement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.taxonomy_classification.model import (
    TaxonomyClassificationWebhookEvent,
    TaxonomyClassificationWebhookWakeup,
)

WebhookEventType = Literal["result.accepted", "job.terminal_non_accepted"]


class TaxonomyClassificationWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    event_type: WebhookEventType
    job_id: PositiveInt
    queue_name: str = Field(min_length=1)
    occurred_at: datetime
    submission_id: PositiveInt | None = None
    terminal_state: str | None = None

    @model_validator(mode="after")
    def validate_event_shape(self) -> TaxonomyClassificationWebhookPayload:
        if self.event_type == "result.accepted" and self.submission_id is None:
            raise ValueError("result.accepted webhook payloads require submission_id")
        if self.event_type == "job.terminal_non_accepted" and self.terminal_state in (None, ""):
            raise ValueError("job.terminal_non_accepted webhook payloads require terminal_state")
        return self


class TaxonomyClassificationWebhookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_event(
        self,
        payload: TaxonomyClassificationWebhookPayload,
    ) -> TaxonomyClassificationWebhookEvent:
        existing = await self._session.scalar(
            select(TaxonomyClassificationWebhookEvent)
            .where(TaxonomyClassificationWebhookEvent.event_id == payload.event_id)
            .limit(1)
        )
        if existing is not None:
            return existing

        record = TaxonomyClassificationWebhookEvent(
            event_id=payload.event_id,
            event_type=payload.event_type,
            job_id=payload.job_id,
            queue_name=payload.queue_name,
            submission_id=payload.submission_id,
            terminal_state=payload.terminal_state,
            occurred_at=payload.occurred_at,
            payload=payload.model_dump(mode="json"),
        )
        self._session.add(record)
        await self._session.flush()

        self._session.add(TaxonomyClassificationWebhookWakeup(event_id=record.event_id))
        await self._session.flush()
        return record

    async def list_pending_events(
        self,
        *,
        limit: int,
    ) -> list[TaxonomyClassificationWebhookEvent]:
        return list(
            await self._session.scalars(
                select(TaxonomyClassificationWebhookEvent)
                .join(
                    TaxonomyClassificationWebhookWakeup,
                    TaxonomyClassificationWebhookWakeup.event_id
                    == TaxonomyClassificationWebhookEvent.event_id,
                )
                .where(TaxonomyClassificationWebhookEvent.processed_at.is_(None))
                .order_by(
                    TaxonomyClassificationWebhookWakeup.id.asc(),
                    TaxonomyClassificationWebhookEvent.created_at.asc(),
                    TaxonomyClassificationWebhookEvent.id.asc(),
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
            delete(TaxonomyClassificationWebhookWakeup).where(
                TaxonomyClassificationWebhookWakeup.event_id == event_id
            )
        )
        await self._session.flush()

    async def mark_failed(
        self,
        *,
        event_id: str,
        last_error: str,
        failed_at: datetime,
    ) -> None:
        record = await self._get_event(event_id)
        record.processed_at = None
        record.last_error = last_error
        record.updated_at = failed_at
        await self._session.flush()

    async def _get_event(self, event_id: str) -> TaxonomyClassificationWebhookEvent:
        record = await self._session.scalar(
            select(TaxonomyClassificationWebhookEvent)
            .where(TaxonomyClassificationWebhookEvent.event_id == event_id)
            .limit(1)
            .with_for_update()
        )
        if record is None:
            raise ValueError(f"Taxonomy-classification webhook event {event_id} does not exist.")
        return record


__all__ = [
    "TaxonomyClassificationWebhookPayload",
    "TaxonomyClassificationWebhookRepository",
    "WebhookEventType",
]
