"""
Abstract: SQLAlchemy persistence projection for taxonomy-classification queue state.
Out of scope: Runtime processing and webhook HTTP authentication.
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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base


class TaxonomyClassificationJob(Base):
    __tablename__ = "taxonomy_classification_jobs"
    __table_args__ = (
        Index(
            "uq_taxonomy_classification_jobs_job_id",
            "job_id",
            unique=True,
            postgresql_where=text("job_id IS NOT NULL"),
        ),
        Index(
            "uq_taxonomy_classification_jobs_active_scope_node",
            "scope_node_id",
            "node_id",
            unique=True,
            postgresql_where=text("processed_at IS NULL AND terminal_state IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxonomy_nodes.id"),
        nullable=False,
    )
    node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    terminal_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
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


class TaxonomyClassificationWebhookEvent(Base):
    __tablename__ = "taxonomy_classification_webhook_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_taxonomy_classification_webhook_events_event_id"),
        Index(
            "ix_taxonomy_classification_webhook_events_pending",
            "processed_at",
            "created_at",
        ),
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


class TaxonomyClassificationWebhookWakeup(Base):
    __tablename__ = "taxonomy_classification_webhook_wakeups"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_taxonomy_classification_webhook_wakeups_event_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("taxonomy_classification_webhook_events.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TaxonomyClassificationContinuationRequest(Base):
    __tablename__ = "taxonomy_classification_continuation_requests"
    __table_args__ = (
        UniqueConstraint(
            "scope_node_id",
            "node_id",
            name="uq_taxonomy_classification_continuation_scope_node",
        ),
        Index(
            "ix_taxonomy_classification_continuation_updated_id",
            "updated_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxonomy_classification_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    next_job_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("taxonomy_classification_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
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


class TaxonomyClassificationProjectionRefreshRequest(Base):
    __tablename__ = "taxonomy_classification_projection_refresh_requests"
    __table_args__ = (
        Index(
            "ix_tax_cls_proj_refresh_updated_at",
            "updated_at",
            "scope_kind",
            "taxonomy_node_id",
        ),
    )

    scope_kind: Mapped[str] = mapped_column(Text, primary_key=True)
    taxonomy_node_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
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


__all__ = [
    "TaxonomyClassificationContinuationRequest",
    "TaxonomyClassificationJob",
    "TaxonomyClassificationProjectionRefreshRequest",
    "TaxonomyClassificationWebhookEvent",
    "TaxonomyClassificationWebhookWakeup",
]
