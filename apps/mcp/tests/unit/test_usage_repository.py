"""
Abstract: Unit tests for MCP usage ledger repository writes.
Out of scope: Database connectivity, Alembic migration execution, and analytics reads.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from knowledge_mcp.usage.repository import SearchUsageEvent, UsageRepository


class FakeSession:
    def __init__(self) -> None:
        self.statements: list[object] = []

    async def execute(self, statement: object) -> None:
        self.statements.append(statement)


@pytest.mark.anyio
async def test_record_search_event_inserts_mcp_usage_row_without_raw_query_or_pat() -> None:
    session = FakeSession()
    repository = UsageRepository(session=session)

    await repository.record_search_event(
        SearchUsageEvent(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            created_at=datetime(2026, 4, 27, tzinfo=UTC),
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
    assert compiled.params["user_sub"] == "user_123"
    assert compiled.params["pat_fingerprint"] == "pat_fingerprint"
    assert "raw search query" not in compiled.params.values()
    assert "raw_pat_secret" not in compiled.params.values()
