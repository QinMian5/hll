"""
Abstract: Repository for recording MCP agent-search analytics facts.
Out of scope: Search usage accounting, quota enforcement, and analytics reads.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

from pydantic import BaseModel, Field
from sqlalchemy import insert

from knowledge_mcp.analytics.model import agent_search_events


class AsyncExecuteSession(Protocol):
    async def execute(self, statement: object) -> object: ...


class MatchedSearchResult(BaseModel):
    node_id: int = Field(gt=0)
    rank: int = Field(ge=1)


class AgentSearchEvent(BaseModel):
    user_sub: str = Field(min_length=1)
    pat_fingerprint: str = Field(min_length=1)
    mcp_session_id: str = Field(min_length=1)
    raw_query: str = Field(min_length=1)
    query_hash: str = Field(min_length=1)
    matched_count: int = Field(ge=0)
    connected_count: int = Field(ge=0)
    matched_results: list[MatchedSearchResult]
    search_algorithm_version: int = Field(ge=1)


class AgentSearchAnalyticsRepository:
    def __init__(self, *, session: AsyncExecuteSession) -> None:
        self._session = session

    async def record_agent_search_event(self, event: AgentSearchEvent) -> None:
        await self._session.execute(
            insert(agent_search_events).values(event.model_dump(mode="python"))
        )


def normalize_query_for_hash(query: str) -> str:
    return " ".join(query.split()).casefold()


def query_hash(query: str) -> str:
    normalized_query = normalize_query_for_hash(query)
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()


__all__ = [
    "AgentSearchAnalyticsRepository",
    "AgentSearchEvent",
    "MatchedSearchResult",
    "normalize_query_for_hash",
    "query_hash",
]
