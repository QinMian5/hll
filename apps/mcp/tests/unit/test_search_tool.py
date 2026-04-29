"""
Abstract: Unit tests for MCP search tool orchestration.
Out of scope: MCP HTTP transport, Logto token exchange, and database connectivity.
"""

from __future__ import annotations

import pytest
from knowledge_contracts_client import MatchedCard, SearchResponse

from knowledge_mcp.analytics.repository import AgentSearchEvent, query_hash
from knowledge_mcp.auth.verifier import AuthenticatedPrincipal
from knowledge_mcp.quota.store import QuotaDecision
from knowledge_mcp.search_tool import QuotaExceededError, SearchTool
from knowledge_mcp.usage.repository import SearchUsageEvent


class FakeSearchService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str) -> SearchResponse:
        self.queries.append(query)
        return SearchResponse(
            matched_cards=[
                MatchedCard(
                    node_id=1,
                    current_version=2,
                    title="Card A",
                    content="Alpha",
                )
            ],
            connected_titles=["Card B"],
        )


class FailingSearchService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str) -> SearchResponse:
        self.queries.append(query)
        raise RuntimeError("search backend failed")


class FakeQuotaStore:
    def __init__(self, decision: QuotaDecision) -> None:
        self.decision = decision
        self.calls: list[tuple[str, str, int]] = []

    async def reserve(
        self,
        *,
        user_sub: str,
        pat_fingerprint: str,
        cost_units: int = 1,
    ) -> QuotaDecision:
        self.calls.append((user_sub, pat_fingerprint, cost_units))
        return self.decision


class FakeUsageRepository:
    def __init__(self) -> None:
        self.events: list[SearchUsageEvent] = []

    async def record_search_event(self, event: SearchUsageEvent) -> None:
        self.events.append(event)


class FakeAgentSearchAnalyticsRepository:
    def __init__(self) -> None:
        self.events: list[AgentSearchEvent] = []

    async def record_agent_search_event(self, event: AgentSearchEvent) -> None:
        self.events.append(event)


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_sub="user_123",
        scopes=frozenset({"search:execute"}),
        pat_fingerprint="pat_fingerprint",
    )


@pytest.mark.anyio
async def test_search_tool_returns_private_search_payload_and_records_usage() -> None:
    search_service = FakeSearchService()
    usage = FakeUsageRepository()
    analytics = FakeAgentSearchAnalyticsRepository()
    tool = SearchTool(
        search_service=search_service,
        quota_store=FakeQuotaStore(QuotaDecision(True, 0, {})),
        usage_repository=usage,
        agent_search_analytics_repository=analytics,
        monotonic_clock=lambda: 10.0,
    )

    result = await tool.search(
        "  Alpha  ",
        principal=_principal(),
        request_id="request-1",
        mcp_session_id="mcp-session-1",
    )

    assert result == {
        "matched_cards": [
            {
                "node_id": 1,
                "current_version": 2,
                "title": "Card A",
                "content": "Alpha",
            }
        ],
        "connected_titles": ["Card B"],
    }
    assert search_service.queries == ["Alpha"]
    assert len(usage.events) == 1
    assert usage.events[0].user_sub == "user_123"
    assert usage.events[0].pat_fingerprint == "pat_fingerprint"
    assert usage.events[0].status == "success"
    assert len(analytics.events) == 1
    assert analytics.events[0].user_sub == "user_123"
    assert analytics.events[0].pat_fingerprint == "pat_fingerprint"
    assert analytics.events[0].mcp_session_id == "mcp-session-1"
    assert analytics.events[0].raw_query == "  Alpha  "
    assert analytics.events[0].query_hash == query_hash("Alpha")
    assert analytics.events[0].matched_count == 1
    assert analytics.events[0].connected_count == 1
    assert [result.model_dump() for result in analytics.events[0].matched_results] == [
        {"node_id": 1, "rank": 1}
    ]
    assert analytics.events[0].search_algorithm_version == 1


@pytest.mark.anyio
async def test_empty_query_is_rejected_before_backend_call() -> None:
    search_service = FakeSearchService()
    tool = SearchTool(
        search_service=search_service,
        quota_store=FakeQuotaStore(QuotaDecision(True, 0, {})),
        usage_repository=FakeUsageRepository(),
        agent_search_analytics_repository=FakeAgentSearchAnalyticsRepository(),
    )

    with pytest.raises(ValueError):
        await tool.search("", principal=_principal(), request_id="request-1")

    assert search_service.queries == []


@pytest.mark.anyio
async def test_quota_exceeded_rejects_without_backend_call_and_records_rejection() -> None:
    search_service = FakeSearchService()
    usage = FakeUsageRepository()
    analytics = FakeAgentSearchAnalyticsRepository()
    tool = SearchTool(
        search_service=search_service,
        quota_store=FakeQuotaStore(QuotaDecision(False, 60, {})),
        usage_repository=usage,
        agent_search_analytics_repository=analytics,
    )

    with pytest.raises(QuotaExceededError):
        await tool.search("alpha", principal=_principal(), request_id="request-1")

    assert search_service.queries == []
    assert len(usage.events) == 1
    assert usage.events[0].user_sub == "user_123"
    assert usage.events[0].pat_fingerprint == "pat_fingerprint"
    assert usage.events[0].status == "quota_rejected"
    assert usage.events[0].error_code == "quota_exceeded"
    assert analytics.events == []


@pytest.mark.anyio
async def test_backend_search_failure_records_usage_error_without_agent_analytics() -> None:
    search_service = FailingSearchService()
    usage = FakeUsageRepository()
    analytics = FakeAgentSearchAnalyticsRepository()
    tool = SearchTool(
        search_service=search_service,
        quota_store=FakeQuotaStore(QuotaDecision(True, 0, {})),
        usage_repository=usage,
        agent_search_analytics_repository=analytics,
        monotonic_clock=lambda: 10.0,
    )

    with pytest.raises(RuntimeError):
        await tool.search("alpha", principal=_principal(), request_id="request-1")

    assert search_service.queries == ["alpha"]
    assert len(usage.events) == 1
    assert usage.events[0].status == "error"
    assert usage.events[0].error_code == "search_failed"
    assert analytics.events == []
