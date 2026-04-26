"""
Abstract: Process entrypoint for the taxonomy-classification webhook receiver.
Out of scope: Docker image construction and public ingress routing.
"""

from __future__ import annotations

import uvicorn

from core.config import (
    TaxonomyClassificationWebhookReceiverSettings,
    load_taxonomy_classification_webhook_receiver_settings,
)
from modules.taxonomy_classification.app import create_taxonomy_classification_webhook_app
from modules.taxonomy_classification.auth import (
    WebhookAuthVerifier,
    WebhookReceiverAuthSettings,
)
from shared.db.session import build_async_engine, build_async_session_factory


def build_auth_settings(
    settings: TaxonomyClassificationWebhookReceiverSettings,
) -> WebhookReceiverAuthSettings:
    return WebhookReceiverAuthSettings(
        issuer=settings.taxonomy_classification_webhook_auth_issuer,
        resource=settings.taxonomy_classification_webhook_auth_resource,
        discovery_url=settings.taxonomy_classification_webhook_auth_discovery_url,
        allowed_client_id=settings.taxonomy_classification_webhook_allowed_client_id,
        http_timeout_seconds=settings.taxonomy_classification_webhook_auth_http_timeout_seconds,
    )


def build_app() -> object:
    settings = load_taxonomy_classification_webhook_receiver_settings()
    engine = build_async_engine(database_url=settings.database_url)
    session_factory = build_async_session_factory(engine=engine)
    return create_taxonomy_classification_webhook_app(
        settings=settings,
        session_factory=session_factory,
        auth_verifier=WebhookAuthVerifier(settings=build_auth_settings(settings)),
    )


app = build_app()


def main() -> None:
    uvicorn.run(
        "entrypoints.taxonomy_classification_webhook_receiver:app",
        host="0.0.0.0",
        port=8080,
    )


__all__ = ["app", "build_app", "build_auth_settings", "main"]
