"""
Abstract: Unit tests for taxonomy-classification webhook receiver app boundaries.
Out of scope: JWT verification internals and database-backed event persistence.
"""

from __future__ import annotations

from typing import NoReturn

from fastapi.testclient import TestClient

from core.config import TaxonomyClassificationWebhookReceiverSettings
from modules.taxonomy_classification.app import create_taxonomy_classification_webhook_app
from modules.taxonomy_classification.auth import WebhookPrincipal


class AcceptingAuthVerifier:
    async def verify_authorization_header(self, authorization: str | None) -> WebhookPrincipal:
        assert authorization == "Bearer token"
        return WebhookPrincipal(subject="job-queue", client_id="job-queue")


class FailingSession:
    async def __aenter__(self) -> FailingSession:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    def begin(self) -> NoReturn:
        raise AssertionError("wrong-queue webhook must not touch the database")


class FailingSessionFactory:
    def __call__(self) -> FailingSession:
        return FailingSession()


def test_webhook_receiver_rejects_wrong_queue_before_recording_event() -> None:
    settings = TaxonomyClassificationWebhookReceiverSettings(
        database_url="postgresql+psycopg://knowledge:secret@postgres:5432/knowledge",
        taxonomy_classification_queue_name="taxonomy_classification",
        taxonomy_classification_webhook_auth_issuer="https://knowledge-logto",
        taxonomy_classification_webhook_auth_resource="https://knowledge-api",
        taxonomy_classification_webhook_auth_discovery_url=(
            "https://knowledge-logto/.well-known/openid-configuration"
        ),
        taxonomy_classification_webhook_allowed_client_id="job-queue",
        taxonomy_classification_webhook_auth_http_timeout_seconds=5.0,
        taxonomy_classification_webhook_public_path="/taxonomy-classification/webhooks/job-queue",
    )
    app = create_taxonomy_classification_webhook_app(
        settings=settings,
        session_factory=FailingSessionFactory(),  # type: ignore[arg-type]
        auth_verifier=AcceptingAuthVerifier(),
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/taxonomy-classification/webhooks/job-queue",
        headers={"Authorization": "Bearer token"},
        json={
            "event_id": "evt-other-queue",
            "event_type": "result.accepted",
            "job_id": 123,
            "queue_name": "page_to_card",
            "occurred_at": "2026-04-26T15:00:00Z",
            "submission_id": 456,
        },
    )

    assert response.status_code == 400
