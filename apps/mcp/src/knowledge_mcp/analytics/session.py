"""
Abstract: Transaction-scoped MCP agent-search analytics recorder.
Out of scope: Analytics table definitions, path analysis, and ClickHouse export.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from knowledge_mcp.analytics.repository import (
    AgentSearchAnalyticsRepository,
    AgentSearchEvent,
    AsyncExecuteSession,
)


class SessionAgentSearchAnalyticsRepository:
    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_agent_search_event(self, event: AgentSearchEvent) -> None:
        async with self._session_factory.begin() as session:
            await AgentSearchAnalyticsRepository(
                session=cast(AsyncExecuteSession, session)
            ).record_agent_search_event(event)


__all__ = ["SessionAgentSearchAnalyticsRepository"]
