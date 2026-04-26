"""
Abstract: Process entrypoint for the source-pipeline webhook receiver.
Out of scope: Docker image construction and nginx ingress routing.
"""

from __future__ import annotations

import uvicorn

from source_pipeline.config import Settings, load_settings
from source_pipeline.db.session import build_session_factory
from source_pipeline.pipeline_webhook.app import create_webhook_receiver_app
from source_pipeline.pipeline_webhook.auth import WebhookAuthVerifier, WebhookReceiverAuthSettings


def build_auth_settings(settings: Settings) -> WebhookReceiverAuthSettings:
    missing = [
        name
        for name, value in {
            "webhook_auth_issuer": settings.webhook_auth_issuer,
            "webhook_auth_resource": settings.webhook_auth_resource,
            "webhook_auth_discovery_url": settings.webhook_auth_discovery_url,
            "webhook_allowed_client_id": settings.webhook_allowed_client_id,
        }.items()
        if value in (None, "")
    ]
    if missing:
        raise ValueError(
            "Webhook receiver auth settings are required: " + ", ".join(sorted(missing))
        )

    assert settings.webhook_auth_issuer is not None
    assert settings.webhook_auth_resource is not None
    assert settings.webhook_auth_discovery_url is not None
    assert settings.webhook_allowed_client_id is not None
    return WebhookReceiverAuthSettings(
        issuer=settings.webhook_auth_issuer,
        resource=settings.webhook_auth_resource,
        discovery_url=settings.webhook_auth_discovery_url,
        allowed_client_id=settings.webhook_allowed_client_id,
        http_timeout_seconds=settings.webhook_auth_http_timeout_seconds,
    )


def build_app() -> object:
    settings = load_settings()
    _, session_factory = build_session_factory(settings)
    return create_webhook_receiver_app(
        settings=settings,
        session_factory=session_factory,
        auth_verifier=WebhookAuthVerifier(settings=build_auth_settings(settings)),
    )


app = build_app()


def main() -> None:
    uvicorn.run(
        "source_pipeline.entrypoints.webhook_receiver:app",
        host="0.0.0.0",
        port=8080,
    )


__all__ = ["app", "build_app", "build_auth_settings", "main"]
