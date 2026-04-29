"""
Abstract: Unit tests for MCP agent-search analytics table projection.
Out of scope: Live PostgreSQL migration execution and search tool behavior.
"""

from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import JSONB

from knowledge_mcp.analytics.model import AgentSearchEventRow, agent_search_events
from knowledge_mcp.db.metadata import metadata


def test_agent_search_events_uses_declarative_mcp_metadata_and_default_schema() -> None:
    assert metadata.schema is None
    assert AgentSearchEventRow.__table__ is agent_search_events
    assert agent_search_events.metadata is metadata
    assert agent_search_events.schema is None
    assert agent_search_events.name == "agent_search_events"


def test_agent_search_events_projection_contains_expected_columns() -> None:
    assert list(agent_search_events.c.keys()) == [
        "id",
        "occurred_at",
        "user_sub",
        "pat_fingerprint",
        "mcp_session_id",
        "raw_query",
        "query_hash",
        "matched_count",
        "connected_count",
        "matched_results",
        "search_algorithm_version",
        "exported_at",
    ]

    required_non_nullable = {
        "id",
        "occurred_at",
        "user_sub",
        "pat_fingerprint",
        "mcp_session_id",
        "raw_query",
        "query_hash",
        "matched_count",
        "connected_count",
        "matched_results",
        "search_algorithm_version",
    }
    for column_name in required_non_nullable:
        assert not agent_search_events.c[column_name].nullable
    assert agent_search_events.c.id.primary_key
    assert isinstance(agent_search_events.c.id.type, Integer)
    assert isinstance(agent_search_events.c.search_algorithm_version.type, Integer)
    assert agent_search_events.c.exported_at.nullable
    assert isinstance(agent_search_events.c.matched_results.type, JSONB)


def test_agent_search_events_defines_analysis_and_export_indexes() -> None:
    index_names = {index.name for index in agent_search_events.indexes}

    assert index_names == {
        "ix_mcp_agent_search_events_export_pending",
        "ix_mcp_agent_search_events_pat_occurred",
        "ix_mcp_agent_search_events_query_hash_occurred",
        "ix_mcp_agent_search_events_session_occurred",
        "ix_mcp_agent_search_events_user_occurred",
    }
