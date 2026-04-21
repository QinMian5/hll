"""
Abstract: SQLAlchemy model projection for source-pipeline orchestration state.
Out of scope: Queue interaction and downstream handoff behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from source_pipeline.db.base import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    config_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class WorkflowUnit(Base):
    __tablename__ = "workflow_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    page_to_card_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class CardReviewJob(Base):
    __tablename__ = "card_review_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workflow_units.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    job_queue_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    handoff_done: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
