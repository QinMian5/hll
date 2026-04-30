"""
Abstract: SQLAlchemy declarative table model for MCP-owned usage ledger writes.
Out of scope: Quota decision logic and usage analytics queries.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import DateTime, Index, Integer, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_mcp.db.metadata import Base


class SearchUsageEventRow(Base):
    __tablename__ = "search_usage_events"
    __table_args__ = (
        Index("ix_mcp_search_usage_events_user_created", "user_sub", "created_at"),
        Index("ix_mcp_search_usage_events_pat_created", "pat_fingerprint", "created_at"),
        Index("ix_mcp_search_usage_events_tool_created", "tool_name", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_sub: Mapped[str] = mapped_column(Text, nullable=False)
    pat_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    query_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False)
    connected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_units: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)


search_usage_events = cast(Table, SearchUsageEventRow.__table__)

__all__ = ["SearchUsageEventRow", "search_usage_events"]
