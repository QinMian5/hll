"""
Abstract: Repository for recording MCP search usage ledger events.
Out of scope: Query hashing policy, quota enforcement, and analytics reads.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field
from sqlalchemy import func, insert, select

from knowledge_mcp.usage.model import search_usage_events
from knowledge_mcp.usage.summary import UsageSummaryRow, dedupe_pat_fingerprints


class AsyncExecuteSession(Protocol):
    async def execute(self, statement: object) -> ExecuteResult: ...


class ExecuteResult(Protocol):
    def mappings(self) -> ExecuteResult: ...
    def all(self) -> list[Mapping[str, object]]: ...


class SearchUsageEvent(BaseModel):
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

    async def get_search_usage_summaries(
        self,
        pat_fingerprints: Sequence[str],
    ) -> list[UsageSummaryRow]:
        unique_fingerprints = dedupe_pat_fingerprints(list(pat_fingerprints))
        if not unique_fingerprints:
            return []

        statement = (
            select(
                search_usage_events.c.pat_fingerprint.label("pat_fingerprint"),
                func.count().label("successful_search_count"),
                func.max(search_usage_events.c.created_at).label("last_used_at"),
            )
            .where(search_usage_events.c.pat_fingerprint.in_(unique_fingerprints))
            .where(search_usage_events.c.tool_name == "search")
            .where(search_usage_events.c.status == "success")
            .group_by(search_usage_events.c.pat_fingerprint)
        )
        result = await self._session.execute(statement)
        rows_by_fingerprint = {str(row["pat_fingerprint"]): row for row in result.mappings().all()}

        summaries: list[UsageSummaryRow] = []
        for fingerprint in unique_fingerprints:
            row = rows_by_fingerprint.get(fingerprint)
            successful_search_count = 0 if row is None else _summary_count(row)
            last_used_at = None if row is None else _summary_last_used_at(row)
            summaries.append(
                UsageSummaryRow(
                    patFingerprint=fingerprint,
                    successfulSearchCount=successful_search_count,
                    last_used_at=last_used_at,
                )
            )
        return summaries


def _summary_count(row: Mapping[str, object]) -> int:
    value = row["successful_search_count"]
    if isinstance(value, int):
        return value
    return int(str(value))


def _summary_last_used_at(row: Mapping[str, object]) -> datetime | None:
    value = row["last_used_at"]
    if value is None or isinstance(value, datetime):
        return value
    raise TypeError("Usage summary last_used_at must be a datetime or None.")
