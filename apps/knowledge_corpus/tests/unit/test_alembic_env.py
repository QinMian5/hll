"""
Abstract: Unit tests for knowledge corpus migration settings loading.
Out of scope: Alembic upgrade execution and revision authoring behavior.
"""

from __future__ import annotations

import pytest

from knowledge_corpus.config import load_migration_settings


def test_alembic_env_uses_knowledge_corpus_migration_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KNOWLEDGE_CORPUS_MIGRATION_DATABASE_URL",
        "postgresql+psycopg://corpus_migration:secret@knowledge_corpus_db:5432/knowledge_corpus",
    )

    assert load_migration_settings().knowledge_corpus_migration_database_url.startswith(
        "postgresql+psycopg://"
    )
