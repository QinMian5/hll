"""
Abstract: Unit tests for the Wikipedia persistence schema projection.
Out of scope: Migration execution and real database I/O behavior.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Table

from knowledge_corpus.wikipedia.model import (
    WikipediaDocument,
    WikipediaProcessedDocument,
)


def test_wikipedia_documents_projection_contains_expected_columns() -> None:
    table = cast(Table, WikipediaDocument.__table__)

    assert list(table.c.keys()) == ["page_id", "url", "title", "clean_text", "search_vector"]


def test_wikipedia_processed_documents_projection_contains_expected_columns() -> None:
    table = cast(Table, WikipediaProcessedDocument.__table__)

    assert list(table.c.keys()) == ["page_id", "processed_at", "external_target_ref"]
