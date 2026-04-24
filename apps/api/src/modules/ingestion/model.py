"""
Abstract: SQLAlchemy persistence projection for ingestion idempotency records.
Out of scope: HTTP header parsing and queue dispatch behavior.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base


class IngestionIdempotencyRecordRow(Base):
    __tablename__ = "ingestion_idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "ingestion_id",
            name="uq_ingestion_idempotency_records_ingestion_id",
        ),
    )

    idempotency_key: Mapped[str] = mapped_column(Text, primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
