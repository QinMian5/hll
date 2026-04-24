"""
Abstract: Async SQLAlchemy repository for ingestion idempotency records.
Out of scope: Queue publish semantics and HTTP transport parsing.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.ingestion.model import IngestionIdempotencyRecordRow


@dataclass(slots=True, frozen=True)
class IngestionIdempotencyRecord:
    idempotency_key: str
    payload_hash: str
    ingestion_id: str


def _record_from_row(row: IngestionIdempotencyRecordRow) -> IngestionIdempotencyRecord:
    return IngestionIdempotencyRecord(
        idempotency_key=row.idempotency_key,
        payload_hash=row.payload_hash,
        ingestion_id=row.ingestion_id,
    )


class IngestionIdempotencyRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(self, *, idempotency_key: str) -> IngestionIdempotencyRecord | None:
        row = await self._session.scalar(
            select(IngestionIdempotencyRecordRow)
            .where(IngestionIdempotencyRecordRow.idempotency_key == idempotency_key)
            .limit(1)
        )
        if row is None:
            return None
        return _record_from_row(row)

    async def create_record(
        self,
        *,
        idempotency_key: str,
        payload_hash: str,
        ingestion_id: str,
    ) -> IngestionIdempotencyRecord:
        row = IngestionIdempotencyRecordRow(
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            ingestion_id=ingestion_id,
        )
        self._session.add(row)
        await self._session.flush()
        return _record_from_row(row)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
