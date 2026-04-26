"""
Abstract: FastAPI app factory for source-pipeline webhook event intake.
Out of scope: Public ingress configuration and runtime event processing.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from source_pipeline.config import Settings
from source_pipeline.pipeline_webhook.auth import (
    WebhookAuthenticationError,
    WebhookPrincipal,
)
from source_pipeline.pipeline_webhook.contracts import JobQueueWebhookPayload
from source_pipeline.pipeline_webhook.repository import JobQueueWebhookEventRepository


class WebhookAuthVerifierPort(Protocol):
    async def verify_authorization_header(
        self,
        authorization: str | None,
    ) -> WebhookPrincipal: ...


def create_webhook_receiver_app(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    auth_verifier: WebhookAuthVerifierPort,
) -> FastAPI:
    app = FastAPI(title="Source Pipeline Webhook Receiver")

    @app.post(settings.webhook_public_path, status_code=status.HTTP_202_ACCEPTED)
    async def receive_job_queue_webhook(
        payload: JobQueueWebhookPayload,
        request: Request,
    ) -> Response:
        try:
            await auth_verifier.verify_authorization_header(request.headers.get("authorization"))
        except WebhookAuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook bearer token.",
            ) from exc

        async with session_factory() as session, session.begin():
            await JobQueueWebhookEventRepository(session).record_event(payload)

        return Response(status_code=status.HTTP_202_ACCEPTED)

    return app


__all__ = ["WebhookAuthVerifierPort", "create_webhook_receiver_app"]
