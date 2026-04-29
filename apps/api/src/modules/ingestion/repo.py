"""
Abstract: Async SQLAlchemy repository for accepted ingestion requests.
Out of scope: Queue publish semantics and HTTP transport parsing.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.ingestion.model import IngestionRequestRow


@dataclass(slots=True, frozen=True)
class IngestionRequest:
    id: int
    idempotency_key: str | None
    payload_hash: str


@dataclass(slots=True, frozen=True)
class IngestionRequestResolution:
    request: IngestionRequest
    created: bool


def _request_from_row(row: IngestionRequestRow) -> IngestionRequest:
    return IngestionRequest(
        id=row.id,
        idempotency_key=row.idempotency_key,
        payload_hash=row.payload_hash,
    )


class IngestionRequestRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, ingestion_id: int) -> IngestionRequest | None:
        row = await self._session.scalar(
            select(IngestionRequestRow).where(IngestionRequestRow.id == ingestion_id).limit(1)
        )
        if row is None:
            return None
        return _request_from_row(row)

    async def get_by_idempotency_key(self, *, idempotency_key: str) -> IngestionRequest | None:
        row = await self._session.scalar(
            select(IngestionRequestRow)
            .where(IngestionRequestRow.idempotency_key == idempotency_key)
            .limit(1)
        )
        if row is None:
            return None
        return _request_from_row(row)

    async def get_or_create_request(
        self,
        *,
        idempotency_key: str | None,
        payload_hash: str,
    ) -> IngestionRequestResolution:
        if idempotency_key is None:
            return IngestionRequestResolution(
                request=await self._create_unkeyed_request(payload_hash=payload_hash),
                created=True,
            )

        statement = (
            insert(IngestionRequestRow)
            .values(idempotency_key=idempotency_key, payload_hash=payload_hash)
            .on_conflict_do_nothing(
                index_elements=["idempotency_key"],
                index_where=IngestionRequestRow.idempotency_key.is_not(None),
            )
            .returning(IngestionRequestRow)
        )
        inserted_row = await self._session.scalar(statement)
        if inserted_row is not None:
            return IngestionRequestResolution(
                request=_request_from_row(inserted_row),
                created=True,
            )

        existing_request = await self.get_by_idempotency_key(idempotency_key=idempotency_key)
        if existing_request is None:
            raise RuntimeError("Idempotency key conflict did not return an existing row.")
        return IngestionRequestResolution(request=existing_request, created=False)

    async def _create_unkeyed_request(self, *, payload_hash: str) -> IngestionRequest:
        row = IngestionRequestRow(
            idempotency_key=None,
            payload_hash=payload_hash,
        )
        self._session.add(row)
        await self._session.flush()
        return _request_from_row(row)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
