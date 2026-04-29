"""
Abstract: SQLAlchemy model projection for source-pipeline orchestration state.
Out of scope: Queue interaction and downstream handoff behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from source_pipeline.db.base import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    config_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class WorkflowUnit(Base):
    __tablename__ = "workflow_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    page_to_card_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to_card_terminal_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CardCandidate(Base):
    __tablename__ = "card_candidates"
    __table_args__ = (
        UniqueConstraint(
            "workflow_unit_id",
            "origin_step",
            "origin_job_id",
            "origin_ordinal",
            name="uq_card_candidates_workflow_origin",
        ),
        UniqueConstraint(
            "parent_candidate_id",
            "origin_step",
            "origin_job_id",
            "origin_ordinal",
            name="uq_card_candidates_parent_origin",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workflow_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_candidate_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("card_candidates.id", ondelete="CASCADE"),
        nullable=True,
    )
    card_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    origin_step: Mapped[str] = mapped_column(Text, nullable=False)
    origin_job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    review_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_terminal_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    repair_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repair_terminal_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_handoff_done: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class JobQueueWebhookEvent(Base):
    __tablename__ = "job_queue_webhook_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_job_queue_webhook_events_event_id"),
        Index("ix_job_queue_webhook_events_pending", "processed_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    queue_name: Mapped[str] = mapped_column(Text, nullable=False)
    submission_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    terminal_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class JobQueueWebhookWakeup(Base):
    __tablename__ = "job_queue_webhook_wakeups"
    __table_args__ = (UniqueConstraint("event_id", name="uq_job_queue_webhook_wakeups_event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("job_queue_webhook_events.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
