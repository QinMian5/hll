"""
Abstract: Integration tests for the source-pipeline webhook receiver app.
Out of scope: Live Logto, public ingress, and orchestrator event processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from source_pipeline.config import Settings
from source_pipeline.db.models import JobQueueWebhookEvent, JobQueueWebhookWakeup
from source_pipeline.pipeline_webhook.app import create_webhook_receiver_app
from source_pipeline.pipeline_webhook.auth import (
    WebhookAuthenticationError,
    WebhookPrincipal,
)

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


@dataclass(frozen=True)
class FakeVerifier:
    async def verify_authorization_header(self, authorization: str | None) -> WebhookPrincipal:
        if authorization != "Bearer valid-token":
            raise WebhookAuthenticationError("invalid token")
        return WebhookPrincipal(
            subject="job-queue-webhook-delivery",
            client_id="job-queue-webhook-delivery",
        )


def build_settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        knowledge_api_base_url="http://knowledge-api:8000",
        job_queue_base_url="http://jq.orbitalis.org/api",
        job_queue_token_url="http://jq-logto.orbitalis.org/oidc/token",
        job_queue_client_id="client-id",
        job_queue_client_secret="client-secret",
        job_queue_resource="https://jq-mcp.orbitalis.org",
        webhook_auth_issuer="https://knowledge-logto.example.com/oidc",
        webhook_auth_resource="https://knowledge.example.com/source-pipeline-webhooks",
        webhook_auth_discovery_url=(
            "https://knowledge-logto.example.com/oidc/.well-known/openid-configuration"
        ),
        webhook_allowed_client_id="job-queue-webhook-delivery",
        webhook_public_path="/source-pipeline/webhooks/job-queue",
    )


def build_payload(event_id: str = "evt-receiver") -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": "result.accepted",
        "job_id": 42,
        "queue_name": "page_to_card",
        "occurred_at": "2026-04-25T15:01:00Z",
        "submission_id": 142,
        "terminal_state": None,
    }


async def build_client(db_engine: AsyncEngine, database_url: str) -> httpx.AsyncClient:
    app = create_webhook_receiver_app(
        settings=build_settings(database_url),
        session_factory=async_sessionmaker(db_engine, expire_on_commit=False),
        auth_verifier=FakeVerifier(),
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


async def test_missing_bearer_token_returns_401(
    db_engine: AsyncEngine,
    test_settings: Settings,
) -> None:
    async with await build_client(db_engine, test_settings.database_url) as client:
        response = await client.post(
            "/source-pipeline/webhooks/job-queue",
            json=build_payload(),
        )

    assert response.status_code == 401


async def test_wrong_bearer_token_returns_401(
    db_engine: AsyncEngine,
    test_settings: Settings,
) -> None:
    async with await build_client(db_engine, test_settings.database_url) as client:
        response = await client.post(
            "/source-pipeline/webhooks/job-queue",
            headers={"Authorization": "Bearer wrong-token"},
            json=build_payload(),
        )

    assert response.status_code == 401


async def test_valid_notification_is_persisted_and_returns_202(
    db_engine: AsyncEngine,
    test_settings: Settings,
) -> None:
    async with await build_client(db_engine, test_settings.database_url) as client:
        response = await client.post(
            "/source-pipeline/webhooks/job-queue",
            headers={"Authorization": "Bearer valid-token"},
            json=build_payload(),
        )

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        persisted = await session.scalar(
            select(JobQueueWebhookEvent).where(JobQueueWebhookEvent.event_id == "evt-receiver")
        )
        wakeup_count = await session.scalar(select(func.count()).select_from(JobQueueWebhookWakeup))

    assert response.status_code == 202
    assert persisted is not None
    assert persisted.job_id == 42
    assert persisted.occurred_at == datetime(2026, 4, 25, 15, 1, tzinfo=UTC)
    assert wakeup_count is not None
    assert wakeup_count >= 1


async def test_duplicate_notification_returns_success_without_duplicate_row(
    db_engine: AsyncEngine,
    test_settings: Settings,
) -> None:
    async with await build_client(db_engine, test_settings.database_url) as client:
        first = await client.post(
            "/source-pipeline/webhooks/job-queue",
            headers={"Authorization": "Bearer valid-token"},
            json=build_payload("evt-duplicate"),
        )
        second = await client.post(
            "/source-pipeline/webhooks/job-queue",
            headers={"Authorization": "Bearer valid-token"},
            json=build_payload("evt-duplicate"),
        )

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        event_count = await session.scalar(
            select(func.count())
            .select_from(JobQueueWebhookEvent)
            .where(JobQueueWebhookEvent.event_id == "evt-duplicate")
        )
        wakeup_count = await session.scalar(
            select(func.count())
            .select_from(JobQueueWebhookWakeup)
            .where(JobQueueWebhookWakeup.event_id == "evt-duplicate")
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert event_count == 1
    assert wakeup_count == 1
