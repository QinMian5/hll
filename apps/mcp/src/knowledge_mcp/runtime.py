"""
Abstract: Dependency composition for the public Knowledge MCP runtime.
Out of scope: ASGI routing, container process management, and migrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, cast

import httpx
from knowledge_contracts_client import SearchClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from knowledge_mcp.auth.context import load_current_principal
from knowledge_mcp.auth.middleware import AccessTokenVerifier, TokenExchangeClient
from knowledge_mcp.auth.service_token import ServiceTokenVerifier, ServiceTokenVerifierSettings
from knowledge_mcp.auth.token_exchange import (
    TokenExchangeClient as LogtoTokenExchangeClient,
)
from knowledge_mcp.auth.token_exchange import (
    TokenExchangeSettings,
)
from knowledge_mcp.auth.verifier import (
    AccessTokenVerifier as LogtoAccessTokenVerifier,
)
from knowledge_mcp.auth.verifier import (
    TokenVerifierSettings,
)
from knowledge_mcp.config import Settings
from knowledge_mcp.internal_api.search import InternalSearchService
from knowledge_mcp.quota.store import QuotaPolicy, QuotaStore, RedisEvalClient
from knowledge_mcp.search_tool import SearchTool
from knowledge_mcp.usage.session import SessionUsageRepository


class AuthMiddlewareKwargs(TypedDict):
    token_exchange_client: TokenExchangeClient
    access_token_verifier: AccessTokenVerifier
    pat_fingerprint_secret: str
    allowed_origins: tuple[str, ...]


@dataclass(slots=True)
class RuntimeResources:
    search_tool: SearchTool
    auth_middleware_kwargs: AuthMiddlewareKwargs
    usage_summary_service: SessionUsageRepository
    quota_summary_service: QuotaStore
    usage_summary_service_token_verifier: ServiceTokenVerifier
    usage_summary_max_batch_size: int
    redis_client: Redis
    auth_http_client: httpx.AsyncClient
    search_http_client: httpx.AsyncClient
    db_engine: AsyncEngine

    async def aclose(self) -> None:
        await self.auth_http_client.aclose()
        await self.search_http_client.aclose()
        await self.redis_client.aclose()
        await self.db_engine.dispose()


def build_runtime_resources(settings: Settings) -> RuntimeResources:
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    auth_http_client = httpx.AsyncClient(timeout=settings.auth_http_timeout_seconds)
    search_http_client = httpx.AsyncClient()
    db_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    token_exchange_client = LogtoTokenExchangeClient(
        settings=TokenExchangeSettings(
            token_url=settings.logto_token_url,
            client_id=settings.logto_token_exchange_client_id,
            client_secret=settings.logto_token_exchange_client_secret,
            resource=settings.logto_resource,
            scopes=settings.logto_required_scopes,
            http_timeout_seconds=settings.auth_http_timeout_seconds,
            token_cache_ttl_seconds=settings.token_cache_ttl_seconds,
        ),
        http_client=auth_http_client,
        redis_client=redis_client,
    )
    access_token_verifier = LogtoAccessTokenVerifier(
        settings=TokenVerifierSettings(
            issuer=settings.logto_issuer,
            resource=settings.logto_resource,
            discovery_url=settings.logto_discovery_url,
            required_scopes=settings.logto_required_scopes,
            http_timeout_seconds=settings.auth_http_timeout_seconds,
        ),
        http_client=auth_http_client,
    )
    usage_summary_service_token_verifier = ServiceTokenVerifier(
        settings=ServiceTokenVerifierSettings(
            issuer=settings.logto_issuer,
            resource=settings.usage_summary_auth_resource,
            discovery_url=settings.logto_discovery_url,
            required_scope=settings.usage_summary_required_scope,
            allowed_client_id=settings.usage_summary_allowed_client_id,
            http_timeout_seconds=settings.auth_http_timeout_seconds,
        )
    )

    quota_store = QuotaStore(
        redis_client=cast(RedisEvalClient, redis_client),
        policy=QuotaPolicy(
            user_daily_limit=settings.user_daily_limit,
            user_daily_window_seconds=settings.user_daily_window_seconds,
            user_weekly_limit=settings.user_weekly_limit,
            user_weekly_window_seconds=settings.user_weekly_window_seconds,
        ),
        prefix=settings.quota_redis_prefix,
    )
    usage_repository = SessionUsageRepository(session_factory=session_factory)
    search_tool = SearchTool(
        search_service=InternalSearchService(
            client=SearchClient(
                base_url=settings.internal_api_base_url,
                http_client=search_http_client,
            )
        ),
        quota_store=quota_store,
        usage_repository=usage_repository,
        principal_provider=load_current_principal,
    )

    return RuntimeResources(
        search_tool=search_tool,
        auth_middleware_kwargs={
            "token_exchange_client": token_exchange_client,
            "access_token_verifier": access_token_verifier,
            "pat_fingerprint_secret": settings.pat_fingerprint_secret,
            "allowed_origins": settings.allowed_origins,
        },
        usage_summary_service=usage_repository,
        quota_summary_service=quota_store,
        usage_summary_service_token_verifier=usage_summary_service_token_verifier,
        usage_summary_max_batch_size=settings.usage_summary_max_batch_size,
        redis_client=redis_client,
        auth_http_client=auth_http_client,
        search_http_client=search_http_client,
        db_engine=db_engine,
    )
