"""
Abstract: Unit tests for app-local runtime and migration settings loading.
Out of scope: SQLAlchemy engine creation and migration execution behavior.
"""

from __future__ import annotations

import pytest

from knowledge_corpus.config import MigrationSettings, Settings, load_migration_settings, load_settings


def test_settings_type_is_defined() -> None:
    assert Settings is not None


def test_migration_settings_type_is_defined() -> None:
    assert MigrationSettings is not None


def test_load_settings_reads_knowledge_corpus_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KNOWLEDGE_CORPUS_DATABASE_URL",
        "postgresql+psycopg://corpus_app:secret@knowledge_corpus_db:5432/knowledge_corpus",
    )
    monkeypatch.setenv(
        "KNOWLEDGE_CORPUS_MIGRATION_DATABASE_URL",
        "postgresql+psycopg://corpus_migration:secret@knowledge_corpus_db:5432/knowledge_corpus",
    )

    settings = load_settings()

    assert settings.knowledge_corpus_database_url.startswith("postgresql+psycopg://")


def test_load_migration_settings_reads_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KNOWLEDGE_CORPUS_MIGRATION_DATABASE_URL",
        "postgresql+psycopg://corpus_migration:secret@knowledge_corpus_db:5432/knowledge_corpus",
    )

    settings = load_migration_settings()

    assert settings.knowledge_corpus_migration_database_url.startswith("postgresql+psycopg://")
