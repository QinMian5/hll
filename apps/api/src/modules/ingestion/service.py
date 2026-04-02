"""
Abstract: Ingestion acceptance service that dispatches async jobs and preserves the
public 202 contract.
Out of scope: FastAPI route wiring and worker-side embedding materialization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from modules.ingestion.schema import IngestionAcceptedResponse, IngestionCreateRequest

logger = logging.getLogger(__name__)


class EnqueueSender(Protocol):
    def send(self, *args: object, **kwargs: object) -> object: ...


def generate_ingestion_id() -> str:
    return f"ing_{uuid4().hex}"


@dataclass(slots=True, kw_only=True)
class IngestionService:
    enqueue_sender: EnqueueSender

    async def accept(
        self,
        *,
        payload: IngestionCreateRequest,
        request_id: str,
    ) -> IngestionAcceptedResponse:
        ingestion_id = generate_ingestion_id()
        try:
            self.enqueue_sender.send(
                ingestion_id,
                request_id,
                payload.title,
                payload.content,
            )
        except Exception as exc:
            logger.exception(
                "ingestion.enqueue_failed",
                extra={
                    "event": "ingestion.enqueue_failed",
                    "request_id": request_id,
                    "ingestion_id": ingestion_id,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )

        return IngestionAcceptedResponse(accepted=True, ingestion_id=ingestion_id)
