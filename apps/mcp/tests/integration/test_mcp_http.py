"""
Abstract: Integration tests for MCP server tool registration.
Out of scope: Live HTTP ingress, Logto, Redis, and PostgreSQL services.
"""

from __future__ import annotations

import pytest
from knowledge_contracts_client import MatchedCard, SearchResponse

from knowledge_mcp.analytics.repository import AgentSearchEvent
from knowledge_mcp.auth.verifier import AuthenticatedPrincipal
from knowledge_mcp.quota.store import QuotaDecision
from knowledge_mcp.search_tool import SearchTool
from knowledge_mcp.server import create_mcp_server


class FakeSearchService:
    async def search(self, query: str) -> SearchResponse:
        return SearchResponse(
            matched_cards=[MatchedCard(title=query, content="content")],
            connected_titles=[],
        )


class FakeQuotaStore:
    async def reserve(
        self,
        *,
        user_sub: str,
        pat_fingerprint: str,
        cost_units: int = 1,
    ) -> QuotaDecision:
        return QuotaDecision(True, 0, {})


class FakeUsageRepository:
    async def record_search_event(self, event: object) -> None:
        return None


class FakeAgentSearchAnalyticsRepository:
    async def record_agent_search_event(self, event: AgentSearchEvent) -> None:
        return None


async def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_sub="user_123",
        scopes=frozenset({"search:execute"}),
        pat_fingerprint="pat_fingerprint",
    )


@pytest.mark.anyio
async def test_mcp_server_exposes_only_search_tool() -> None:
    search_tool = SearchTool(
        search_service=FakeSearchService(),
        quota_store=FakeQuotaStore(),
        usage_repository=FakeUsageRepository(),
        agent_search_analytics_repository=FakeAgentSearchAnalyticsRepository(),
        principal_provider=_principal,
    )
    server = create_mcp_server(search_tool=search_tool)

    tools = await server.list_tools()

    assert [tool.name for tool in tools] == ["search"]
