"""
Abstract: Repository for recording MCP search usage ledger events.
Out of scope: Query hashing policy, quota enforcement, and analytics reads.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import insert

from knowledge_mcp.usage.model import search_usage_events


class AsyncExecuteSession(Protocol):
    async def execute(self, statement: object) -> object: ...


class SearchUsageEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str = Field(min_length=1)
    user_sub: str = Field(min_length=1)
    pat_fingerprint: str = Field(min_length=1)
    tool_name: str = Field(default="search", min_length=1)
    query_hash: str = Field(min_length=1)
    status: str = Field(min_length=1)
    error_code: str | None = None
    matched_count: int = Field(ge=0)
    connected_count: int = Field(ge=0)
    cost_units: int = Field(ge=1)
    duration_ms: int = Field(ge=0)


class UsageRepository:
    def __init__(self, *, session: AsyncExecuteSession) -> None:
        self._session = session

    async def record_search_event(self, event: SearchUsageEvent) -> None:
        await self._session.execute(
            insert(search_usage_events).values(event.model_dump(mode="python"))
        )
