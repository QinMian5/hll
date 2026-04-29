"""
Abstract: Unit tests for MCP-owned Alembic migration boundaries.
Out of scope: Live PostgreSQL migration execution and Docker startup behavior.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Integer

from knowledge_mcp.analytics.model import agent_search_events
from knowledge_mcp.db.metadata import metadata
from knowledge_mcp.usage.model import SearchUsageEventRow, search_usage_events

REPO_ROOT = Path(__file__).resolve().parents[4]
API_ALEMBIC_ENV = REPO_ROOT / "apps" / "api" / "alembic" / "env.py"
API_ALEMBIC_VERSIONS = REPO_ROOT / "apps" / "api" / "alembic" / "versions"
MCP_ALEMBIC_ENV = REPO_ROOT / "apps" / "mcp" / "alembic" / "env.py"
MCP_ALEMBIC_INI = REPO_ROOT / "apps" / "mcp" / "alembic.ini"


def test_mcp_owns_its_alembic_environment() -> None:
    assert MCP_ALEMBIC_INI.exists()
    assert MCP_ALEMBIC_ENV.exists()

    env = MCP_ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "target_metadata = metadata" in env
    assert "include_schemas=True" not in env
    assert "version_table_schema" not in env


def test_api_alembic_does_not_register_mcp_usage_models() -> None:
    api_env = API_ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "mcp_usage" not in api_env
    assert "agent_search_events" not in api_env
    assert "include_schemas=True" not in api_env

    for revision in API_ALEMBIC_VERSIONS.glob("*.py"):
        revision_text = revision.read_text(encoding="utf-8")
        assert "mcp_usage" not in revision_text
        assert "agent_search_events" not in revision_text


def test_mcp_alembic_does_not_provision_login_roles() -> None:
    env = MCP_ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "CREATE ROLE" not in env
    assert "_ensure_runtime_role" not in env


def test_mcp_usage_table_uses_dedicated_database_default_schema() -> None:
    assert metadata.schema is None
    assert SearchUsageEventRow.__table__ is search_usage_events
    assert search_usage_events.schema is None
    assert search_usage_events.name == "search_usage_events"
    assert search_usage_events.c.id.primary_key
    assert isinstance(search_usage_events.c.id.type, Integer)
    assert agent_search_events.schema is None
    assert agent_search_events.name == "agent_search_events"


def test_mcp_usage_table_defines_audit_lookup_indexes() -> None:
    index_names = {index.name for index in search_usage_events.indexes}

    assert index_names == {
        "ix_mcp_search_usage_events_pat_created",
        "ix_mcp_search_usage_events_tool_created",
        "ix_mcp_search_usage_events_user_created",
    }


def test_mcp_agent_search_events_defines_analysis_lookup_indexes() -> None:
    index_names = {index.name for index in agent_search_events.indexes}

    assert index_names == {
        "ix_mcp_agent_search_events_export_pending",
        "ix_mcp_agent_search_events_pat_occurred",
        "ix_mcp_agent_search_events_query_hash_occurred",
        "ix_mcp_agent_search_events_session_occurred",
        "ix_mcp_agent_search_events_user_occurred",
    }
