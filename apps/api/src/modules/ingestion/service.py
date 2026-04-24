"""
Abstract: Ingestion acceptance service that dispatches async jobs and preserves the
public 202 contract.
Out of scope: FastAPI route wiring and worker-side embedding materialization.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from core.errors import ApplicationError, ErrorCode
from modules.ingestion.queue import IngestionTask
from modules.ingestion.repo import IngestionIdempotencyRecord
from modules.ingestion.schema import IngestionAcceptedResponse, IngestionCreateRequest

logger = logging.getLogger(__name__)


class IngestionTaskPublisher(Protocol):
    def __call__(self, task: IngestionTask) -> None: ...


class IngestionIdempotencyRepoProtocol(Protocol):
    async def get_by_key(self, *, idempotency_key: str) -> IngestionIdempotencyRecord | None: ...

    async def create_record(
        self,
        *,
        idempotency_key: str,
        payload_hash: str,
        ingestion_id: str,
    ) -> IngestionIdempotencyRecord: ...

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


def generate_ingestion_id() -> str:
    return f"ing_{uuid4().hex}"


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
    idempotency_repo: IngestionIdempotencyRepoProtocol | None = None

    async def accept(
        self,
        *,
        payload: IngestionCreateRequest,
        request_id: str,
        idempotency_key: str | None = None,
    ) -> IngestionAcceptedResponse:
        normalized_key = "" if idempotency_key is None else idempotency_key.strip()
        if normalized_key:
            return await self._accept_idempotent(
                payload=payload,
                request_id=request_id,
                idempotency_key=normalized_key,
            )

        return self._accept_non_idempotent(payload=payload, request_id=request_id)

    def _accept_non_idempotent(
        self,
        *,
        payload: IngestionCreateRequest,
        request_id: str,
    ) -> IngestionAcceptedResponse:
        ingestion_id = generate_ingestion_id()
        task = IngestionTask(
            ingestion_id=ingestion_id,
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

        return IngestionAcceptedResponse(accepted=True, ingestion_id=task.ingestion_id)

    async def _accept_idempotent(
        self,
        *,
        payload: IngestionCreateRequest,
        request_id: str,
        idempotency_key: str,
    ) -> IngestionAcceptedResponse:
        if self.idempotency_repo is None:
            raise RuntimeError("Ingestion idempotency requires an idempotency repository.")

        payload_hash = _payload_hash(payload)
        existing_record = await self.idempotency_repo.get_by_key(idempotency_key=idempotency_key)
        if existing_record is not None:
            if existing_record.payload_hash != payload_hash:
                raise IngestionIdempotencyConflictError(idempotency_key=idempotency_key)
            return IngestionAcceptedResponse(
                accepted=True,
                ingestion_id=existing_record.ingestion_id,
            )

        ingestion_id = generate_ingestion_id()
        task = IngestionTask(
            ingestion_id=ingestion_id,
            request_id=request_id,
            title=payload.title,
            content=payload.content,
        )
        try:
            await self.idempotency_repo.create_record(
                idempotency_key=idempotency_key,
                payload_hash=payload_hash,
                ingestion_id=ingestion_id,
            )
        except Exception:
            await self.idempotency_repo.rollback()
            raise

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
            await self.idempotency_repo.rollback()
            raise

        try:
            await self.idempotency_repo.commit()
        except Exception:
            await self.idempotency_repo.rollback()
            raise

        return IngestionAcceptedResponse(accepted=True, ingestion_id=task.ingestion_id)
