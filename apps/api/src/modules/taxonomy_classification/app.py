"""
Abstract: FastAPI app factory for taxonomy-classification webhook intake.
Out of scope: Public ingress configuration and runtime result processing.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from modules.taxonomy_classification.auth import (
    WebhookAuthenticationError,
    WebhookPrincipal,
)
from modules.taxonomy_classification.webhook import (
    TaxonomyClassificationWebhookPayload,
    TaxonomyClassificationWebhookRepository,
)


class WebhookAuthVerifierPort(Protocol):
    async def verify_authorization_header(
        self,
        authorization: str | None,
    ) -> WebhookPrincipal: ...


class WebhookReceiverSettingsPort(Protocol):
    taxonomy_classification_queue_name: str
    taxonomy_classification_webhook_public_path: str


def create_taxonomy_classification_webhook_app(
    *,
    settings: WebhookReceiverSettingsPort,
    session_factory: async_sessionmaker[AsyncSession],
    auth_verifier: WebhookAuthVerifierPort,
) -> FastAPI:
    app = FastAPI(title="Taxonomy Classification Webhook Receiver")

    @app.post(
        settings.taxonomy_classification_webhook_public_path,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def receive_job_queue_webhook(
        payload: TaxonomyClassificationWebhookPayload,
        request: Request,
    ) -> Response:
        try:
            await auth_verifier.verify_authorization_header(request.headers.get("authorization"))
        except WebhookAuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook bearer token.",
            ) from exc
        if payload.queue_name != settings.taxonomy_classification_queue_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unexpected webhook queue.",
            )

        async with session_factory() as session, session.begin():
            await TaxonomyClassificationWebhookRepository(session).record_event(payload)

        return Response(status_code=status.HTTP_202_ACCEPTED)

    return app


__all__ = [
    "WebhookAuthVerifierPort",
    "WebhookReceiverSettingsPort",
    "create_taxonomy_classification_webhook_app",
]
