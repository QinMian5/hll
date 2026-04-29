"""
Abstract: SQLAlchemy persistence projection for accepted ingestion requests.
Out of scope: HTTP header parsing and queue dispatch behavior.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base


class IngestionRequestRow(Base):
    __tablename__ = "ingestion_requests"
    __table_args__ = (
        Index(
            "ix_ingestion_requests_idempotency_key_unique",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
