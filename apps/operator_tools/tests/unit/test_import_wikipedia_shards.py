"""
Abstract: Contract tests for the external Wikipedia-to-knowledge-corpus importer scaffold.
Out of scope: Marker-state transitions, database import execution, and worker coordination.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace, TracebackType

import pytest

import knowledge_operator.knowledge_corpus.import_wikipedia_shards as importer
from knowledge_operator.knowledge_corpus.import_wikipedia_shards import (
    ShardImportSummary,
    _acquire_import_lock,
    _import_shard_worker_async,
    _release_import_lock,
    build_document_record,
    build_import_plan,
    build_import_progress_snapshot,
    claim_shard,
    classify_resume_candidates,
    discover_article_shards,
    load_total_document_hint,
    run_import,
    write_completed_marker,
    write_failed_marker,
    write_running_marker,
)


@pytest.fixture(autouse=True)
def reset_worker_cached_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importer, "_WORKER_ENGINE", None)
    monkeypatch.setattr(importer, "_WORKER_SESSION_FACTORY", None)
    monkeypatch.setattr(importer, "_WORKER_DATABASE_URL", None)


def test_discover_article_shards_returns_sorted_jsonl_zst_files(tmp_path: Path) -> None:
    articles_root = tmp_path / "articles"
    (articles_root / "split-00002").mkdir(parents=True)
    (articles_root / "split-00001").mkdir(parents=True)

    expected = [
        articles_root / "split-00001" / "shard-00000.jsonl.zst",
        articles_root / "split-00002" / "shard-00001.jsonl.zst",
    ]
    for path in reversed(expected):
        path.write_bytes(b"stub")

    assert discover_article_shards(articles_root) == expected


def test_build_document_record_maps_preprocessed_article_payload() -> None:
    record = build_document_record(
        {
            "page_id": 1,
            "title": "Physics",
            "source_url": "https://en.wikipedia.org/wiki/Physics",
            "clean_text": "Physics studies matter and energy.",
        }
    )

    assert record.page_id == 1
    assert record.title == "Physics"


def test_claim_shard_creates_running_marker(tmp_path: Path) -> None:
    shard_path = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    shard_path.parent.mkdir(parents=True)
    shard_path.write_bytes(b"stub")
    state_root = tmp_path / "state"

    claimed = claim_shard(shard_path, state_root=state_root, worker_id="worker-1")

    assert claimed.status == "running"
    assert claimed.marker_path.name == "shard-00000.running.json"
    assert (
        json.loads(claimed.marker_path.read_text(encoding="utf-8"))["worker_id"]
        == "worker-1"
    )


def test_resume_skips_completed_and_reclaims_stale_running(tmp_path: Path) -> None:
    first_shard = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    second_shard = tmp_path / "articles" / "split-00001" / "shard-00001.jsonl.zst"
    first_shard.parent.mkdir(parents=True)
    first_shard.write_bytes(b"alpha")
    second_shard.write_bytes(b"beta")
    state_root = tmp_path / "state"

    write_completed_marker(first_shard, state_root=state_root, worker_id="worker-1")
    stale_running = write_running_marker(
        second_shard, state_root=state_root, worker_id="old-worker"
    )

    resumable = classify_resume_candidates(
        [first_shard, second_shard], state_root=state_root
    )

    assert first_shard not in resumable
    assert second_shard in resumable
    assert stale_running.status == "running"


def test_build_import_plan_counts_completed_and_retryable_shards(
    tmp_path: Path,
) -> None:
    articles_root = tmp_path / "articles"
    state_root = tmp_path / "state"
    shards: list[Path] = []
    for shard_index in range(3):
        shard_path = (
            articles_root / "split-00001" / f"shard-{shard_index:05d}.jsonl.zst"
        )
        shard_path.parent.mkdir(parents=True, exist_ok=True)
        shard_path.write_bytes(b"stub")
        shards.append(shard_path)

    write_completed_marker(shards[0], state_root=state_root, worker_id="worker-1")
    write_failed_marker(shards[1], state_root=state_root, worker_id="worker-2")

    plan = build_import_plan(articles_root=articles_root, state_root=state_root)

    assert plan.total_shards == 3
    assert plan.completed_shards == 1
    assert plan.pending_or_retryable_shards == 2


def test_load_total_document_hint_reads_preprocess_run_stats(tmp_path: Path) -> None:
    articles_root = tmp_path / "runs" / "run-00001" / "articles"
    stats_root = articles_root.parent / "stats"
    stats_root.mkdir(parents=True)
    (stats_root / "run.json").write_text(
        json.dumps({"records": {"canonical_article": 12345}}),
        encoding="utf-8",
    )

    assert load_total_document_hint(articles_root) == 12345


def test_build_import_progress_snapshot_reports_eta_inputs() -> None:
    snapshot = build_import_progress_snapshot(
        total_shards=10,
        completed_shards=4,
        failed_shards=1,
        running_shards=2,
        records_seen=5000,
        records_committed=4500,
        batches_committed=9,
        double_claims=0,
        total_documents=10000,
        started_at_monotonic=10.0,
        now_monotonic=20.0,
        status="running",
    )

    assert snapshot["total_documents"] == 10000
    assert snapshot["records_committed"] == 4500
    assert snapshot["docs_per_second"] == 450.0
    assert snapshot["completed_shards"] == 4


@pytest.mark.anyio
async def test_worker_async_reuses_engine_for_same_database_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shard_path = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    shard_path.parent.mkdir(parents=True)
    shard_path.write_bytes(b"stub")

    build_calls: list[str] = []

    async def fake_dispose() -> None:
        return None

    fake_engine = SimpleNamespace(dispose=fake_dispose)
    fake_session_factory = object()

    def fake_build_session_factory(_settings: object) -> tuple[object, object]:
        build_calls.append("called")
        return fake_engine, fake_session_factory

    async def fake_import_article_shard(
        _shard_path: Path,
        *,
        session_factory: object,
        batch_size: int,
    ) -> ShardImportSummary:
        assert session_factory is fake_session_factory
        assert batch_size == 10
        return ShardImportSummary(
            shard_id=_shard_path.stem,
            records_seen=1,
            records_committed=1,
            batches_committed=1,
        )

    monkeypatch.setattr(
        importer,
        "build_session_factory",
        fake_build_session_factory,
    )
    monkeypatch.setattr(
        importer,
        "import_article_shard",
        fake_import_article_shard,
    )

    await _import_shard_worker_async(
        shard_path=shard_path,
        batch_size=10,
        database_url="postgresql+psycopg://worker:test@localhost/db",
    )
    await _import_shard_worker_async(
        shard_path=shard_path,
        batch_size=10,
        database_url="postgresql+psycopg://worker:test@localhost/db",
    )

    assert build_calls == ["called"]


@pytest.mark.anyio
async def test_worker_async_disposes_old_engine_when_database_url_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shard_path = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    shard_path.parent.mkdir(parents=True)
    shard_path.write_bytes(b"stub")

    disposed_urls: list[str] = []
    build_calls: list[str] = []
    session_factories = [object(), object()]
    engines = [
        SimpleNamespace(dispose=lambda: _record_dispose(disposed_urls, "db-1")),
        SimpleNamespace(dispose=lambda: _record_dispose(disposed_urls, "db-2")),
    ]

    def fake_build_session_factory(_settings: object) -> tuple[object, object]:
        index = len(build_calls)
        build_calls.append(f"db-{index + 1}")
        return engines[index], session_factories[index]

    async def fake_import_article_shard(
        _shard_path: Path,
        *,
        session_factory: object,
        batch_size: int,
    ) -> ShardImportSummary:
        assert session_factory in session_factories
        assert batch_size == 10
        return ShardImportSummary(
            shard_id=_shard_path.stem,
            records_seen=1,
            records_committed=1,
            batches_committed=1,
        )

    monkeypatch.setattr(
        importer,
        "build_session_factory",
        fake_build_session_factory,
    )
    monkeypatch.setattr(
        importer,
        "import_article_shard",
        fake_import_article_shard,
    )

    await _import_shard_worker_async(
        shard_path=shard_path,
        batch_size=10,
        database_url="postgresql+psycopg://worker:test@localhost/db-1",
    )
    await _import_shard_worker_async(
        shard_path=shard_path,
        batch_size=10,
        database_url="postgresql+psycopg://worker:test@localhost/db-2",
    )

    assert build_calls == ["db-1", "db-2"]
    assert disposed_urls == ["db-1"]


async def _record_dispose(disposed_urls: list[str], label: str) -> None:
    disposed_urls.append(label)


def test_run_import_interrupts_all_workers_and_records_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shard_path = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    shard_path.parent.mkdir(parents=True)
    shard_path.write_bytes(b"stub")
    state_root = tmp_path / "state"

    events: list[tuple[str, dict[str, object]]] = []
    interrupted_executors: list[object] = []

    class FakeFuture:
        def done(self) -> bool:
            return False

    class FakeExecutor:
        def __init__(self, *, max_workers: int) -> None:
            self.max_workers = max_workers
            self.submitted: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def __enter__(self) -> FakeExecutor:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def submit(self, *args: object, **kwargs: object) -> FakeFuture:
            self.submitted.append((args, kwargs))
            return FakeFuture()

    fake_executor = FakeExecutor(max_workers=1)

    monkeypatch.setattr(
        importer,
        "ProcessPoolExecutor",
        lambda max_workers: fake_executor,
    )
    monkeypatch.setattr(
        importer,
        "as_completed",
        lambda _futures: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr(
        importer,
        "_interrupt_executor_tree",
        lambda executor: interrupted_executors.append(executor),
    )
    monkeypatch.setattr(
        importer,
        "_append_event",
        lambda *, state_root, event_type, payload: events.append((event_type, payload)),
    )
    monkeypatch.setattr(
        importer,
        "load_settings",
        lambda: SimpleNamespace(
            database_url="postgresql+psycopg://worker:test@localhost/db"
        ),
    )

    with pytest.raises(KeyboardInterrupt):
        run_import(
            articles_root=tmp_path / "articles",
            state_root=state_root,
            workers=1,
            batch_size=10,
            progress=False,
        )

    assert interrupted_executors == [fake_executor]
    assert ("import-interrupted", {"running_shards": 1}) in events


def test_run_import_interrupts_executor_when_ctrl_c_happens_during_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shard_path = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    shard_path.parent.mkdir(parents=True)
    shard_path.write_bytes(b"stub")
    state_root = tmp_path / "state"

    events: list[tuple[str, dict[str, object]]] = []
    interrupted_executors: list[object] = []

    class FakeExecutor:
        def __init__(self, *, max_workers: int) -> None:
            self.max_workers = max_workers

        def __enter__(self) -> FakeExecutor:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            return None

        def submit(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("submit should not be reached when claim interrupts")

    fake_executor = FakeExecutor(max_workers=1)
    monkeypatch.setattr(
        importer,
        "ProcessPoolExecutor",
        lambda max_workers: fake_executor,
    )
    monkeypatch.setattr(
        importer,
        "_claim_or_reclaim_shard",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr(
        importer,
        "_interrupt_executor_tree",
        lambda executor: interrupted_executors.append(executor),
    )
    monkeypatch.setattr(
        importer,
        "_append_event",
        lambda *, state_root, event_type, payload: events.append((event_type, payload)),
    )
    monkeypatch.setattr(
        importer,
        "load_settings",
        lambda: SimpleNamespace(
            database_url="postgresql+psycopg://worker:test@localhost/db"
        ),
    )

    with pytest.raises(KeyboardInterrupt):
        run_import(
            articles_root=tmp_path / "articles",
            state_root=state_root,
            workers=1,
            batch_size=10,
            progress=False,
        )

    assert interrupted_executors == [fake_executor]
    assert ("import-interrupted", {"running_shards": 0}) in events


def test_run_import_fails_fast_when_same_state_root_is_already_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shard_path = tmp_path / "articles" / "split-00001" / "shard-00000.jsonl.zst"
    shard_path.parent.mkdir(parents=True)
    shard_path.write_bytes(b"stub")
    state_root = tmp_path / "state"
    state_root.mkdir(parents=True, exist_ok=True)
    lock_handle = _acquire_import_lock(state_root)
    try:
        monkeypatch.setattr(
            importer,
            "load_settings",
            lambda: SimpleNamespace(
                database_url="postgresql+psycopg://worker:test@localhost/db"
            ),
        )
        with pytest.raises(RuntimeError, match="import already running"):
            run_import(
                articles_root=tmp_path / "articles",
                state_root=state_root,
                workers=1,
                batch_size=10,
                progress=False,
            )
    finally:
        _release_import_lock(lock_handle)
