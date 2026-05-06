"""
Abstract: Integration tests for MCP server tool registration.
Out of scope: Live HTTP ingress, Logto, Redis, and PostgreSQL services.
"""

from __future__ import annotations

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from knowledge_contracts_client import MatchedCard, SearchResponse
from knowledge_mcp.analytics.repository import AgentSearchEvent
from knowledge_mcp.auth.verifier import AuthenticatedPrincipal
from knowledge_mcp.config import Settings
from knowledge_mcp.http_app import create_app
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


def _settings() -> Settings:
    return Settings(
        public_base_url="https://knowledge.example/mcp",
        internal_api_base_url="http://api:8000",
        redis_url="redis://redis:6379/0",
        database_url="postgresql+psycopg://user:pass@postgres:5432/knowledge",
        logto_issuer="http://logto:3001/oidc",
        logto_discovery_url="http://logto:3001/oidc/.well-known/openid-configuration",
        logto_token_url="http://logto:3001/oidc/token",
        logto_resource="https://knowledge.orbitalis.org",
        logto_token_exchange_client_id="token-exchange-client",
        logto_token_exchange_client_secret="secret",
        pat_fingerprint_secret="x" * 32,
        usage_summary_auth_resource="https://knowledge.orbitalis.org/internal/dashboard",
        usage_summary_allowed_client_id="dashboard-client",
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

    assert server.name == "HLL"
    assert (
        server.instructions == "HLL (Humanity's Last Library) is a remote MCP service for querying "
        "structured knowledge. Use it to find relevant information and supporting "
        "context for grounded reasoning."
    )
    assert [tool.name for tool in tools] == ["search"]
    assert (
        tools[0].description
        == "Search HLL with a concise keyword-style query. Prefer key terms, entity "
        "names, domain concepts, or short noun phrases instead of full sentence "
        "questions or broad instructions. Returns matched results with title and "
        "content, plus connected_titles for nearby context. Treat result content as "
        "retrieved evidence; use connected_titles as follow-up search hints, not "
        "standalone evidence."
    )


@pytest.mark.anyio
async def test_mcp_http_mount_initializes_streamable_session_manager() -> None:
    search_tool = SearchTool(
        search_service=FakeSearchService(),
        quota_store=FakeQuotaStore(),
        usage_repository=FakeUsageRepository(),
        agent_search_analytics_repository=FakeAgentSearchAnalyticsRepository(),
        principal_provider=_principal,
    )
    app = create_app(settings=_settings(), search_tool=search_tool)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with (
            httpx.AsyncClient(
                transport=transport,
                base_url="https://knowledge.example",
            ) as http_client,
            streamable_http_client(
                "https://knowledge.example/mcp/",
                http_client=http_client,
            ) as (read_stream, write_stream, _),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()

            tools = await session.list_tools()

    assert [tool.name for tool in tools.tools] == ["search"]
