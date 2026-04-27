"""
Abstract: Transaction-scoped MCP usage recorder for runtime database sessions.
Out of scope: Usage table definitions, analytics reads, and quota policy.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from knowledge_mcp.usage.repository import AsyncExecuteSession, SearchUsageEvent, UsageRepository


class SessionUsageRepository:
    def __init__(self, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_search_event(self, event: SearchUsageEvent) -> None:
        async with self._session_factory.begin() as session:
            await UsageRepository(session=cast(AsyncExecuteSession, session)).record_search_event(
                event
            )
