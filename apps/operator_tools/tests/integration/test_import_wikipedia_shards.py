"""
Abstract: Integration tests for streamed Wikipedia shard import into knowledge corpus.
Out of scope: Multi-process coordination, marker-file recovery, and terminal progress UI.
"""

from __future__ import annotations

import builtins
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import knowledge_operator.knowledge_corpus.import_wikipedia_shards as importer
from knowledge_corpus.wikipedia.model import WikipediaDocument
from knowledge_operator.knowledge_corpus.import_wikipedia_shards import (
    import_article_shard,
    run_import,
)

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


async def _fetch_page_ids(session: AsyncSession) -> list[int]:
    result = await session.scalars(
        select(WikipediaDocument.page_id).order_by(WikipediaDocument.page_id)
    )
    return list(result)


async def _count_documents(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(WikipediaDocument)) or 0


async def test_import_article_shard_streams_records_into_wikipedia_documents(
    sample_article_shard: Path,
    knowledge_corpus_session_factory: async_sessionmaker[AsyncSession],
    truncate_wikipedia_tables_before_test: None,
) -> None:
    summary = await import_article_shard(
        sample_article_shard,
        session_factory=knowledge_corpus_session_factory,
        batch_size=2,
    )

    assert summary.records_seen == 3
    assert summary.records_committed == 3
    assert summary.batches_committed == 2

    async with knowledge_corpus_session_factory() as session:
        assert await _fetch_page_ids(session) == [100, 101, 102]


async def test_import_article_shard_is_idempotent_for_replayed_shards(
    sample_article_shard: Path,
    knowledge_corpus_session_factory: async_sessionmaker[AsyncSession],
    truncate_wikipedia_tables_before_test: None,
) -> None:
    await import_article_shard(
        sample_article_shard,
        session_factory=knowledge_corpus_session_factory,
        batch_size=1,
    )
    await import_article_shard(
        sample_article_shard,
        session_factory=knowledge_corpus_session_factory,
        batch_size=1,
    )

    async with knowledge_corpus_session_factory() as session:
        assert await _fetch_page_ids(session) == [100, 101, 102]


async def test_run_import_claims_each_shard_once(
    multi_shard_articles_root: Path,
    knowledge_corpus_database_url: str,
    tmp_path: Path,
    clean_wikipedia_tables: None,
    knowledge_corpus_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    state_root = tmp_path / "state"

    result = run_import(
        articles_root=multi_shard_articles_root,
        state_root=state_root,
        workers=2,
        batch_size=2,
        progress=False,
        database_url=knowledge_corpus_database_url,
    )

    assert result.completed_shards == 3
    assert result.failed_shards == 0
    assert result.double_claims == 0

    progress_payload = json.loads(
        (state_root / "stats" / "progress.json").read_text(encoding="utf-8")
    )
    assert progress_payload["completed_shards"] == 3
    assert progress_payload["failed_shards"] == 0

    async with knowledge_corpus_session_factory() as session:
        assert await _count_documents(session) == 6


async def test_run_import_progress_uses_reporter_instead_of_per_shard_print(
    multi_shard_articles_root: Path,
    knowledge_corpus_database_url: str,
    tmp_path: Path,
    clean_wikipedia_tables: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshots: list[dict[str, object]] = []

    class RecordingReporter:
        def __call__(self, snapshot: dict[str, object]) -> None:
            snapshots.append(snapshot)

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        importer,
        "build_progress_reporter",
        lambda: RecordingReporter(),
    )
    monkeypatch.setattr(
        builtins,
        "print",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("print should not be used")),
    )

    result = run_import(
        articles_root=multi_shard_articles_root,
        state_root=tmp_path / "state",
        workers=2,
        batch_size=2,
        progress=True,
        database_url=knowledge_corpus_database_url,
    )

    assert result.completed_shards == 3
    assert snapshots
    assert snapshots[-1]["completed_shards"] == 3
    assert snapshots[-1]["status"] == "completed"
