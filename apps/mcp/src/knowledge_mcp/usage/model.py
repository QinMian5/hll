"""
Abstract: SQLAlchemy table definition for MCP-owned usage ledger writes.
Out of scope: Quota decision logic and usage analytics queries.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, Integer, MetaData, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

metadata = MetaData()

search_usage_events = Table(
    "search_usage_events",
    metadata,
    Column("id", PostgreSQLUUID(as_uuid=True), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("request_id", Text, nullable=False),
    Column("user_sub", Text, nullable=False),
    Column("pat_fingerprint", Text, nullable=False),
    Column("tool_name", Text, nullable=False),
    Column("query_hash", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("error_code", Text, nullable=True),
    Column("matched_count", Integer, nullable=False),
    Column("connected_count", Integer, nullable=False),
    Column("cost_units", Integer, nullable=False),
    Column("duration_ms", Integer, nullable=False),
    Index("ix_mcp_search_usage_events_user_created", "user_sub", "created_at"),
    Index("ix_mcp_search_usage_events_pat_created", "pat_fingerprint", "created_at"),
    Index("ix_mcp_search_usage_events_tool_created", "tool_name", "created_at"),
)

__all__ = ["metadata", "search_usage_events"]
