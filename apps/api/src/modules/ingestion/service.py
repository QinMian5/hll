"""
Abstract: Ingestion acceptance service that records accepted requests and dispatches async jobs.
Out of scope: FastAPI route wiring and worker-side embedding materialization.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Protocol

from core.errors import ApplicationError, ErrorCode, InfrastructureError
from modules.ingestion.queue import IngestionTask
from modules.ingestion.repo import IngestionRequestResolution
from modules.ingestion.schema import IngestionAcceptedResponse, IngestionCreateRequest

logger = logging.getLogger(__name__)


class IngestionTaskPublisher(Protocol):
    def __call__(self, task: IngestionTask) -> None: ...


class IngestionRequestRepoProtocol(Protocol):
    async def get_or_create_request(
        self,
        *,
        idempotency_key: str | None,
        payload_hash: str,
    ) -> IngestionRequestResolution: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class IngestionIdempotencyConflictError(ApplicationError):
    def __init__(self, *, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(
            code=ErrorCode.APPLICATION_INGESTION_STATE_CONFLICT,
            message="Idempotency key was already used with a different payload.",
            hint="Use the same payload for this idempotency key or choose a new key.",
        )


def _payload_hash(payload: IngestionCreateRequest) -> str:
    serialized_payload = json.dumps(
        {
            "content": payload.content,
            "title": payload.title,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


@dataclass(slots=True, kw_only=True)
class IngestionService:
    task_publisher: IngestionTaskPublisher
    ingestion_repo: IngestionRequestRepoProtocol

    async def accept(
        self,
        *,
        payload: IngestionCreateRequest,
        request_id: str,
        idempotency_key: str | None = None,
    ) -> IngestionAcceptedResponse:
        normalized_key = None if idempotency_key is None else idempotency_key.strip() or None
        payload_hash = _payload_hash(payload)
        try:
            resolution = await self.ingestion_repo.get_or_create_request(
                idempotency_key=normalized_key,
                payload_hash=payload_hash,
            )
        except Exception:
            await self.ingestion_repo.rollback()
            raise
        ingestion_request = resolution.request

        if not resolution.created:
            if ingestion_request.payload_hash != payload_hash:
                if normalized_key is None:
                    raise RuntimeError("Unkeyed ingestion request unexpectedly reused a row.")
                raise IngestionIdempotencyConflictError(idempotency_key=normalized_key)
            return IngestionAcceptedResponse(
                accepted=True,
                ingestion_id=ingestion_request.id,
            )

        task = IngestionTask(
            ingestion_id=ingestion_request.id,
            request_id=request_id,
            title=payload.title,
            content=payload.content,
        )
        try:
            self.task_publisher(task)
        except Exception as exc:
            logger.exception(
                "ingestion.enqueue_failed",
                extra={
                    "event": "ingestion.enqueue_failed",
                    "request_id": task.request_id,
                    "ingestion_id": task.ingestion_id,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )
            await self.ingestion_repo.rollback()
            raise InfrastructureError(
                code=ErrorCode.INFRA_QUEUE_UNAVAILABLE,
                message="Ingestion queue is unavailable.",
                hint="Retry after the queue service recovers.",
                log_details={
                    "request_id": task.request_id,
                    "ingestion_id": task.ingestion_id,
                    "error_class": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            ) from exc

        try:
            await self.ingestion_repo.commit()
        except Exception:
            await self.ingestion_repo.rollback()
            raise

        return IngestionAcceptedResponse(accepted=True, ingestion_id=task.ingestion_id)
