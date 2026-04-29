"""
Abstract: MCP search tool orchestration across auth principal, quota, search, and usage.
Out of scope: MCP transport routing and Logto token exchange.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from typing import Protocol

from knowledge_contracts_client import SearchResponse

from knowledge_mcp.analytics.repository import (
    AgentSearchEvent,
    MatchedSearchResult,
)
from knowledge_mcp.analytics.repository import (
    query_hash as analytics_query_hash,
)
from knowledge_mcp.auth.verifier import AuthenticatedPrincipal
from knowledge_mcp.quota.store import QuotaDecision
from knowledge_mcp.usage.repository import SearchUsageEvent

SEARCH_ALGORITHM_VERSION = 1


class SearchService(Protocol):
    async def search(self, query: str) -> SearchResponse: ...


class QuotaStore(Protocol):
    async def reserve(
        self,
        *,
        user_sub: str,
        pat_fingerprint: str,
        cost_units: int = 1,
    ) -> QuotaDecision: ...


class UsageRepository(Protocol):
    async def record_search_event(self, event: SearchUsageEvent) -> None: ...


class AgentSearchAnalyticsRepository(Protocol):
    async def record_agent_search_event(self, event: AgentSearchEvent) -> None: ...


PrincipalProvider = Callable[[], Awaitable[AuthenticatedPrincipal]]


class QuotaExceededError(ValueError):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__("MCP search quota exceeded.")
        self.retry_after_seconds = retry_after_seconds


class SearchTool:
    def __init__(
        self,
        *,
        search_service: SearchService,
        quota_store: QuotaStore,
        usage_repository: UsageRepository,
        agent_search_analytics_repository: AgentSearchAnalyticsRepository,
        principal_provider: PrincipalProvider | None = None,
        search_algorithm_version: int = SEARCH_ALGORITHM_VERSION,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._search_service = search_service
        self._quota_store = quota_store
        self._usage_repository = usage_repository
        self._agent_search_analytics_repository = agent_search_analytics_repository
        self._principal_provider = principal_provider
        self._search_algorithm_version = search_algorithm_version
        self._monotonic_clock = monotonic_clock

    async def search(
        self,
        query: str,
        *,
        principal: AuthenticatedPrincipal | None = None,
        request_id: str = "unknown",
        mcp_session_id: str = "unknown",
    ) -> dict[str, object]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty.")

        resolved_principal = principal or await self._load_principal()
        quota_decision = await self._quota_store.reserve(
            user_sub=resolved_principal.user_sub,
            pat_fingerprint=resolved_principal.pat_fingerprint,
            cost_units=1,
        )
        if not quota_decision.allowed:
            await self._record_usage(
                principal=resolved_principal,
                request_id=request_id,
                query=normalized_query,
                status="quota_rejected",
                error_code="quota_exceeded",
                matched_count=0,
                connected_count=0,
                duration_ms=0,
            )
            raise QuotaExceededError(retry_after_seconds=quota_decision.retry_after_seconds)

        start = self._monotonic_clock()
        try:
            response = await self._search_service.search(normalized_query)
        except Exception:
            await self._record_usage(
                principal=resolved_principal,
                request_id=request_id,
                query=normalized_query,
                status="error",
                error_code="search_failed",
                matched_count=0,
                connected_count=0,
                duration_ms=self._elapsed_ms(start),
            )
            raise

        await self._record_usage(
            principal=resolved_principal,
            request_id=request_id,
            query=normalized_query,
            status="success",
            error_code=None,
            matched_count=len(response.matched_cards),
            connected_count=len(response.connected_titles),
            duration_ms=self._elapsed_ms(start),
        )
        await self._record_agent_search_analytics(
            principal=resolved_principal,
            mcp_session_id=mcp_session_id,
            raw_query=query,
            response=response,
        )
        return {
            "matched_cards": [card.model_dump(mode="json") for card in response.matched_cards],
            "connected_titles": response.connected_titles,
        }

    async def _load_principal(self) -> AuthenticatedPrincipal:
        if self._principal_provider is None:
            raise RuntimeError("MCP principal provider is not configured.")
        return await self._principal_provider()

    async def _record_usage(
        self,
        *,
        principal: AuthenticatedPrincipal,
        request_id: str,
        query: str,
        status: str,
        error_code: str | None,
        matched_count: int,
        connected_count: int,
        duration_ms: int,
    ) -> None:
        await self._usage_repository.record_search_event(
            SearchUsageEvent(
                request_id=request_id,
                user_sub=principal.user_sub,
                pat_fingerprint=principal.pat_fingerprint,
                query_hash=_query_hash(query),
                status=status,
                error_code=error_code,
                matched_count=matched_count,
                connected_count=connected_count,
                cost_units=1,
                duration_ms=duration_ms,
            )
        )

    async def _record_agent_search_analytics(
        self,
        *,
        principal: AuthenticatedPrincipal,
        mcp_session_id: str,
        raw_query: str,
        response: SearchResponse,
    ) -> None:
        await self._agent_search_analytics_repository.record_agent_search_event(
            AgentSearchEvent(
                user_sub=principal.user_sub,
                pat_fingerprint=principal.pat_fingerprint,
                mcp_session_id=mcp_session_id,
                raw_query=raw_query,
                query_hash=analytics_query_hash(raw_query),
                matched_count=len(response.matched_cards),
                connected_count=len(response.connected_titles),
                matched_results=[
                    MatchedSearchResult(node_id=card.node_id, rank=index)
                    for index, card in enumerate(response.matched_cards, start=1)
                ],
                search_algorithm_version=self._search_algorithm_version,
            )
        )

    def _elapsed_ms(self, start: float) -> int:
        return max(0, int((self._monotonic_clock() - start) * 1000))


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()
