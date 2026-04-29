"""
Abstract: SQLAlchemy declarative table model for MCP agent-search analytics facts.
Out of scope: Analytics capture orchestration and query-hash policy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_mcp.db.metadata import Base


class AgentSearchEventRow(Base):
    __tablename__ = "agent_search_events"
    __table_args__ = (
        Index("ix_mcp_agent_search_events_session_occurred", "mcp_session_id", "occurred_at"),
        Index("ix_mcp_agent_search_events_user_occurred", "user_sub", "occurred_at"),
        Index("ix_mcp_agent_search_events_pat_occurred", "pat_fingerprint", "occurred_at"),
        Index("ix_mcp_agent_search_events_query_hash_occurred", "query_hash", "occurred_at"),
        Index(
            "ix_mcp_agent_search_events_export_pending",
            "occurred_at",
            postgresql_where=text("exported_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    user_sub: Mapped[str] = mapped_column(Text, nullable=False)
    pat_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    mcp_session_id: Mapped[str] = mapped_column(Text, nullable=False)
    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    query_hash: Mapped[str] = mapped_column(Text, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False)
    connected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    search_algorithm_version: Mapped[int] = mapped_column(Integer, nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


agent_search_events = AgentSearchEventRow.__table__

__all__ = ["AgentSearchEventRow", "agent_search_events"]
