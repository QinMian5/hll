"""
Abstract: Unit tests for app-local SQLAlchemy engine and session-factory wiring.
Out of scope: Real PostgreSQL connectivity and migration lifecycle behavior.
"""

from __future__ import annotations

import pytest

from knowledge_corpus.config import load_settings
from knowledge_corpus.db.session import build_session_factory


def test_session_factory_uses_app_local_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KNOWLEDGE_CORPUS_DATABASE_URL",
        "postgresql+psycopg://corpus_app:secret@knowledge_corpus_db:5432/knowledge_corpus",
    )

    engine, session_factory = build_session_factory(load_settings())

    assert engine.url.drivername == "postgresql+psycopg"
    assert session_factory is not None
