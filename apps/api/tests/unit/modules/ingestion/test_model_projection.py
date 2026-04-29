"""
Abstract: Unit tests for ingestion persistence model projection.
Out of scope: Migration execution and queue dispatch behavior.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Index, Table

from modules.ingestion.model import IngestionRequestRow
from shared.db.base import Base


def test_projection_registers_ingestion_requests_table() -> None:
    assert "ingestion_requests" in Base.metadata.tables


def test_ingestion_requests_idempotency_key_uses_partial_unique_index() -> None:
    table = cast(Table, IngestionRequestRow.__table__)
    matching_indexes = [
        index
        for index in table.indexes
        if isinstance(index, Index)
        and index.unique
        and {column.name for column in index.columns} == {"idempotency_key"}
    ]

    assert matching_indexes
    predicate = str(matching_indexes[0].dialect_options["postgresql"]["where"])
    assert "idempotency_key IS NOT NULL" in predicate
    assert table.c.id.primary_key is True
    assert table.c.idempotency_key.nullable is True
