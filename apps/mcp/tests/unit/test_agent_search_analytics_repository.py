"""
Abstract: Unit tests for MCP agent-search analytics repository writes.
Out of scope: Live database connectivity and search tool capture behavior.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from knowledge_mcp.analytics.repository import (
    AgentSearchAnalyticsRepository,
    AgentSearchEvent,
    MatchedSearchResult,
    normalize_query_for_hash,
    query_hash,
)


class FakeSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    async def execute(self, statement: object) -> None:
        self.statements.append(statement)


@pytest.mark.anyio
async def test_record_agent_search_event_inserts_append_only_analytics_row() -> None:
    session = FakeSession()
    repository = AgentSearchAnalyticsRepository(session=session)

    await repository.record_agent_search_event(
        AgentSearchEvent(
            user_sub="user_123",
            pat_fingerprint="pat_fingerprint",
            mcp_session_id="mcp-session-1",
            raw_query="  Graph   Search  ",
            query_hash=query_hash("  Graph   Search  "),
            matched_count=2,
            connected_count=3,
            matched_results=[
                MatchedSearchResult(node_id=10, rank=1),
                MatchedSearchResult(node_id=20, rank=2),
            ],
            search_algorithm_version=1,
        )
    )

    assert len(session.statements) == 1
    compiled = session.statements[0].compile()
    assert "agent_search_events" in str(compiled)
    assert "search_usage_events" not in str(compiled)
    assert "id" not in compiled.params
    assert "occurred_at" not in compiled.params
    assert "exported_at" not in compiled.params
    assert "request_id" not in compiled.params
    assert compiled.params["raw_query"] == "  Graph   Search  "
    assert compiled.params["mcp_session_id"] == "mcp-session-1"
    assert compiled.params["search_algorithm_version"] == 1
    assert compiled.params["query_hash"] == query_hash("graph search")
    assert compiled.params["matched_results"] == [
        {"node_id": 10, "rank": 1},
        {"node_id": 20, "rank": 2},
    ]
    assert "raw_pat_secret" not in compiled.params.values()


def test_query_hash_uses_deterministic_whitespace_and_case_normalization() -> None:
    assert normalize_query_for_hash("  Graph   Search\tPATH  ") == "graph search path"
    assert (
        query_hash("  Graph   Search\tPATH  ") == hashlib.sha256(b"graph search path").hexdigest()
    )
    assert query_hash("graph search path") == query_hash("GRAPH   SEARCH PATH")
