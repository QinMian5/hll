"""
Abstract: Unit tests for MCP runtime dependency composition.
Out of scope: Live network connections and container process startup.
"""

from __future__ import annotations

import pytest

from knowledge_mcp.config import Settings
from knowledge_mcp.runtime import build_runtime_resources
from knowledge_mcp.search_tool import SearchTool


def _settings() -> Settings:
    return Settings(
        public_base_url="https://knowledge.example.com",
        internal_api_base_url="http://api:8000",
        redis_url="redis://redis:6379/0",
        database_url="postgresql+psycopg://mcp:secret@mcp_db:5432/knowledge_mcp",
        logto_issuer="https://logto.example.com/oidc",
        logto_discovery_url="https://logto.example.com/oidc/.well-known/openid-configuration",
        logto_token_url="https://logto.example.com/oidc/token",
        logto_resource="https://knowledge.example.com/mcp",
        logto_token_exchange_client_id="mcp-token-exchange",
        logto_token_exchange_client_secret="secret",
        pat_fingerprint_secret="x" * 32,
        allowed_origins=("https://knowledge.example.com",),
        usage_summary_auth_resource="https://knowledge.example.com/mcp-internal",
        usage_summary_allowed_client_id="web-dashboard-bff",
        user_daily_limit=1000,
        user_daily_window_seconds=86_400,
        user_weekly_limit=5000,
        user_weekly_window_seconds=604_800,
    )


@pytest.mark.anyio
async def test_runtime_resources_wire_search_tool_and_auth_middleware_dependencies() -> None:
    resources = build_runtime_resources(_settings())
    try:
        assert isinstance(resources.search_tool, SearchTool)
        assert resources.auth_middleware_kwargs["pat_fingerprint_secret"] == "x" * 32
        assert resources.auth_middleware_kwargs["allowed_origins"] == (
            "https://knowledge.example.com",
        )
        assert resources.quota_summary_service is resources.search_tool._quota_store
    finally:
        await resources.aclose()
