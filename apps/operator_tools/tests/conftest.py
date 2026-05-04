"""
Abstract: Shared pytest fixtures for operator tools tests.
Out of scope: Production data loading and source-pipeline runtime orchestration.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import zstandard as zstd
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from knowledge_corpus.config import Settings, load_settings
from knowledge_corpus.db.session import build_engine


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def knowledge_corpus_settings() -> Settings:
    try:
        return load_settings()
    except ValidationError as exc:
        raise pytest.UsageError(
            "operator tools integration tests require KNOWLEDGE_CORPUS_DATABASE_URL."
        ) from exc


@pytest.fixture(scope="session")
def knowledge_corpus_database_url(knowledge_corpus_settings: Settings) -> str:
    return knowledge_corpus_settings.database_url


@pytest.fixture(scope="session")
async def knowledge_corpus_engine(
    knowledge_corpus_database_url: str,
) -> AsyncIterator[AsyncEngine]:
    engine = build_engine(database_url=knowledge_corpus_database_url)
    try:
        async with engine.connect() as connection:
            await connection.scalar(text("SELECT current_database()"))
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def knowledge_corpus_session_factory(
    knowledge_corpus_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        knowledge_corpus_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest.fixture
async def clean_wikipedia_tables(
    knowledge_corpus_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    await _truncate_wikipedia_tables(knowledge_corpus_session_factory)
    yield
    await _truncate_wikipedia_tables(knowledge_corpus_session_factory)


@pytest.fixture
async def truncate_wikipedia_tables_before_test(
    clean_wikipedia_tables: None,
) -> None:
    return None


@pytest.fixture
def sample_article_shard(tmp_path: Path) -> Path:
    shard_path = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    _write_article_shard(
        shard_path,
        [
            _article_record(100, "Physics"),
            _article_record(101, "Chemistry"),
            _article_record(102, "Biology"),
        ],
    )
    return shard_path


@pytest.fixture
def multi_shard_articles_root(tmp_path: Path) -> Path:
    articles_root = tmp_path / "articles"
    for shard_index in range(3):
        shard_path = articles_root / "split-00001" / f"shard-{shard_index:05d}.jsonl.zst"
        base_page_id = 200 + (shard_index * 2)
        _write_article_shard(
            shard_path,
            [
                _article_record(base_page_id, f"Topic {base_page_id}"),
                _article_record(base_page_id + 1, f"Topic {base_page_id + 1}"),
            ],
        )
    return articles_root


async def _truncate_wikipedia_tables(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await session.execute(
            text("TRUNCATE wikipedia.processed_documents, wikipedia.documents CASCADE")
        )
        await session.commit()


def _write_article_shard(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(f"{json.dumps(record, sort_keys=True)}\n" for record in records)
    path.write_bytes(zstd.ZstdCompressor().compress(payload.encode("utf-8")))


def _article_record(page_id: int, title: str) -> dict[str, object]:
    slug = title.replace(" ", "_")
    return {
        "page_id": page_id,
        "source_url": f"https://en.wikipedia.org/wiki/{slug}",
        "title": title,
        "clean_text": f"{title} is a concise sample article for importer tests.",
    }
