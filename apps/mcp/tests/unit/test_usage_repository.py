"""
Abstract: Unit tests for MCP usage ledger repository writes.
Out of scope: Database connectivity, Alembic migration execution, and analytics reads.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from knowledge_mcp.usage.repository import SearchUsageEvent, UsageRepository

PAT_A = "pat_" + ("a" * 64)
PAT_B = "pat_" + ("b" * 64)


class FakeSession:
    def __init__(self, rows: list[Mapping[str, object]] | None = None) -> None:
        self.statements: list[Any] = []
        self.rows = rows or []

    async def execute(self, statement: object) -> FakeResult:
        self.statements.append(statement)
        return FakeResult(self.rows)


class FakeResult:
    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> FakeResult:
        return self

    def all(self) -> list[Mapping[str, object]]:
        return self._rows


@pytest.mark.anyio
async def test_record_search_event_inserts_mcp_usage_row_without_raw_query_or_pat() -> None:
    session = FakeSession()
    repository = UsageRepository(session=session)

    await repository.record_search_event(
        SearchUsageEvent(
            request_id="request-1",
            user_sub="user_123",
            pat_fingerprint="pat_fingerprint",
            query_hash="query_hash",
            status="success",
            error_code=None,
            matched_count=2,
            connected_count=3,
            cost_units=1,
            duration_ms=25,
        )
    )

    assert len(session.statements) == 1
    compiled = session.statements[0].compile()
    assert "search_usage_events" in str(compiled)
    assert "mcp_usage.search_usage_events" not in str(compiled)
    assert "id" not in compiled.params
    assert "created_at" not in compiled.params
    assert compiled.params["user_sub"] == "user_123"
    assert compiled.params["pat_fingerprint"] == "pat_fingerprint"
    assert "raw search query" not in compiled.params.values()
    assert "raw_pat_secret" not in compiled.params.values()


@pytest.mark.anyio
async def test_get_search_usage_summaries_counts_successful_search_events_per_pat() -> None:
    last_used_at = datetime(2026, 4, 28, 10, tzinfo=UTC)
    session = FakeSession(
        rows=[
            {
                "pat_fingerprint": PAT_A,
                "successful_search_count": 3,
                "last_used_at": last_used_at,
            }
        ]
    )
    repository = UsageRepository(session=session)

    summaries = await repository.get_search_usage_summaries([PAT_A, PAT_A, PAT_B])

    assert [summary.pat_fingerprint for summary in summaries] == [PAT_A, PAT_B]
    assert summaries[0].successful_search_count == 3
    assert summaries[0].last_used_at == last_used_at
    assert summaries[1].successful_search_count == 0
    assert summaries[1].last_used_at is None
    assert len(session.statements) == 1
    compiled = session.statements[0].compile()
    assert "search_usage_events" in str(compiled)
    assert "count" in str(compiled).lower()
    assert "max" in str(compiled).lower()
    assert "raw_pat_secret" not in compiled.params.values()
