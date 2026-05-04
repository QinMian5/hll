"""
Abstract: Recoverable external importer for loading preprocessed Wikipedia articles.
Out of scope: Processed-document workflows, source filtering, and online API integration.
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import fcntl
import io
import json
import os
import sys
import time
from collections.abc import Iterator
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TextIO, cast

import zstandard as zstd
from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from knowledge_corpus.config import Settings, load_settings
from knowledge_corpus.db.session import build_session_factory
from knowledge_corpus.wikipedia.service import upsert_documents
from knowledge_corpus.wikipedia.types import WikipediaDocumentRecord

ShardStatus = Literal["running", "completed", "failed"]

_WORKER_ENGINE: AsyncEngine | None = None
_WORKER_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None
_WORKER_DATABASE_URL: str | None = None


class _ProcessHandle(Protocol):
    def is_alive(self) -> bool: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def join(self, timeout: float) -> None: ...


@dataclass(slots=True, frozen=True)
class ShardMarker:
    shard_id: str
    input_path: Path
    marker_path: Path
    status: ShardStatus
    worker_id: str


@dataclass(slots=True, frozen=True)
class ShardImportSummary:
    shard_id: str
    records_seen: int
    records_committed: int
    batches_committed: int


@dataclass(slots=True, frozen=True)
class ImportPlan:
    shard_paths: tuple[Path, ...]
    total_shards: int
    completed_shards: int
    pending_or_retryable_shards: int


@dataclass(slots=True, frozen=True)
class ImportRunResult:
    total_shards: int
    completed_shards: int
    failed_shards: int
    double_claims: int
    records_seen: int
    records_committed: int
    batches_committed: int


class TerminalProgressReporter:
    def __init__(self) -> None:
        self._rendered_lines = 0

    def __call__(self, snapshot: dict[str, object]) -> None:
        lines = self._render_lines(snapshot)
        if self._rendered_lines:
            print(f"\x1b[{self._rendered_lines}A", end="", file=sys.stderr)
        for line in lines:
            print(f"\x1b[2K{line}", file=sys.stderr)
        self._rendered_lines = len(lines)
        if snapshot.get("status") != "running":
            self.close()

    def close(self) -> None:
        if self._rendered_lines:
            print("", file=sys.stderr)
        self._rendered_lines = 0

    def _render_lines(self, snapshot: dict[str, object]) -> list[str]:
        total_documents = snapshot.get("total_documents")
        committed = _snapshot_int(snapshot, "records_committed")
        total_shards = _snapshot_int(snapshot, "total_shards")
        completed_shards = _snapshot_int(snapshot, "completed_shards")
        rate = _snapshot_float(snapshot, "docs_per_second")
        return [
            (
                f"Docs   {self._format_bar(committed, total_documents)} "
                f"{committed}/{total_documents if total_documents is not None else '?'} "
                f"| {rate:.1f} docs/s"
            ),
            (
                f"Shards {self._format_bar(completed_shards, total_shards)} "
                f"{completed_shards}/{total_shards} "
                f"| running={_snapshot_int(snapshot, 'running_shards')} "
                f"failed={_snapshot_int(snapshot, 'failed_shards')}"
            ),
        ]

    def _format_bar(self, current: int, total: object, *, width: int = 28) -> str:
        if not isinstance(total, int) or total <= 0:
            filled = max(1, width // 4)
            return f"[{'#' * filled}{'.' * (width - filled)}]"
        ratio = max(0.0, min(1.0, current / total))
        filled = int(width * ratio)
        return f"[{'#' * filled}{'.' * (width - filled)}]"


class RichProgressReporter:
    def __init__(self) -> None:
        self._console = Console(stderr=True)
        self._progress = Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=28),
            MofNCompleteColumn(),
            TextColumn("{task.fields[details]}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self._console,
            expand=True,
        )
        self._docs_task_id = self._progress.add_task(
            "Docs",
            total=1,
            completed=0,
            details="0.0 docs/s",
        )
        self._shards_task_id = self._progress.add_task(
            "Shards",
            total=1,
            completed=0,
            details="0 active | fail=0",
        )
        self._live = Live(
            self._progress,
            console=self._console,
            refresh_per_second=10,
            transient=False,
        )
        self._started = False

    def __call__(self, snapshot: dict[str, object]) -> None:
        if not self._started:
            self._live.start()
            self._started = True

        total_documents_value = snapshot.get("total_documents")
        total_documents = (
            int(total_documents_value)
            if isinstance(total_documents_value, int) and total_documents_value > 0
            else max(1, _snapshot_int(snapshot, "records_committed"))
        )
        self._progress.update(
            self._docs_task_id,
            total=total_documents,
            completed=_snapshot_int(snapshot, "records_committed"),
            details=f"{_snapshot_float(snapshot, 'docs_per_second'):.1f} docs/s",
        )
        self._progress.update(
            self._shards_task_id,
            total=max(1, _snapshot_int(snapshot, "total_shards")),
            completed=_snapshot_int(snapshot, "completed_shards"),
            details=(
                f"{_snapshot_int(snapshot, 'running_shards')} active | "
                f"fail={_snapshot_int(snapshot, 'failed_shards')}"
            ),
        )
        self._live.refresh()
        if snapshot.get("status") != "running":
            self.close()

    def close(self) -> None:
        if self._started:
            self._live.stop()
            self._started = False


def build_progress_reporter() -> TerminalProgressReporter | RichProgressReporter:
    return RichProgressReporter()


def discover_article_shards(articles_root: Path) -> list[Path]:
    return sorted(articles_root.glob("split-*/shard-*.jsonl.zst"))


def build_document_record(payload: dict[str, object]) -> WikipediaDocumentRecord:
    return WikipediaDocumentRecord(
        page_id=int(str(payload["page_id"])),
        url=str(payload["source_url"]),
        title=str(payload["title"]),
        clean_text=str(payload["clean_text"]),
    )


def _snapshot_int(snapshot: dict[str, object], key: str, default: int = 0) -> int:
    value = snapshot.get(key, default)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    return default


def _snapshot_float(snapshot: dict[str, object], key: str, default: float = 0.0) -> float:
    value = snapshot.get(key, default)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return default


def claim_shard(shard_path: Path, *, state_root: Path, worker_id: str) -> ShardMarker:
    marker = _marker_for(
        shard_path, state_root=state_root, status="running", worker_id=worker_id
    )
    marker.marker_path.parent.mkdir(parents=True, exist_ok=True)
    with marker.marker_path.open("x", encoding="utf-8") as handle:
        json.dump(_marker_payload(marker), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return marker


def write_running_marker(
    shard_path: Path, *, state_root: Path, worker_id: str
) -> ShardMarker:
    marker = _marker_for(
        shard_path, state_root=state_root, status="running", worker_id=worker_id
    )
    _replace_marker(marker)
    return marker


def write_completed_marker(
    shard_path: Path, *, state_root: Path, worker_id: str
) -> ShardMarker:
    marker = _marker_for(
        shard_path, state_root=state_root, status="completed", worker_id=worker_id
    )
    _replace_marker(marker)
    return marker


def write_failed_marker(
    shard_path: Path, *, state_root: Path, worker_id: str
) -> ShardMarker:
    marker = _marker_for(
        shard_path, state_root=state_root, status="failed", worker_id=worker_id
    )
    _replace_marker(marker)
    return marker


def classify_resume_candidates(
    shard_paths: list[Path], *, state_root: Path
) -> list[Path]:
    resumable: list[Path] = []
    for shard_path in shard_paths:
        if (
            _find_existing_marker(shard_path, state_root=state_root, status="completed")
            is not None
        ):
            continue
        resumable.append(shard_path)
    return resumable


def build_import_plan(
    *,
    articles_root: Path,
    state_root: Path,
    limit_shards: int | None = None,
) -> ImportPlan:
    shard_paths = discover_article_shards(articles_root)
    if limit_shards is not None:
        shard_paths = shard_paths[:limit_shards]
    resumable = classify_resume_candidates(shard_paths, state_root=state_root)
    completed = len(shard_paths) - len(resumable)
    return ImportPlan(
        shard_paths=tuple(resumable),
        total_shards=len(shard_paths),
        completed_shards=completed,
        pending_or_retryable_shards=len(resumable),
    )


def load_total_document_hint(articles_root: Path) -> int | None:
    run_stats_path = articles_root.parent / "stats" / "run.json"
    if not run_stats_path.exists():
        return None
    try:
        payload = json.loads(run_stats_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    records = payload.get("records")
    if not isinstance(records, dict):
        return None
    canonical_article = records.get("canonical_article")
    if isinstance(canonical_article, int) and canonical_article > 0:
        return canonical_article
    return None


def build_import_progress_snapshot(
    *,
    total_shards: int,
    completed_shards: int,
    failed_shards: int,
    running_shards: int,
    records_seen: int,
    records_committed: int,
    batches_committed: int,
    double_claims: int,
    total_documents: int | None,
    started_at_monotonic: float,
    now_monotonic: float | None = None,
    status: str,
) -> dict[str, object]:
    current_monotonic = now_monotonic if now_monotonic is not None else time.monotonic()
    elapsed_seconds = max(0.001, current_monotonic - started_at_monotonic)
    return {
        "status": status,
        "total_shards": total_shards,
        "completed_shards": completed_shards,
        "failed_shards": failed_shards,
        "running_shards": running_shards,
        "records_seen": records_seen,
        "records_committed": records_committed,
        "batches_committed": batches_committed,
        "double_claims": double_claims,
        "total_documents": total_documents,
        "elapsed_seconds": elapsed_seconds,
        "docs_per_second": records_committed / elapsed_seconds,
    }


def iter_article_records(shard_path: Path) -> Iterator[WikipediaDocumentRecord]:
    with shard_path.open("rb") as compressed_handle:
        decompressor = zstd.ZstdDecompressor()
        with decompressor.stream_reader(compressed_handle) as reader:
            text_reader = io.TextIOWrapper(reader, encoding="utf-8")
            try:
                for raw_line in text_reader:
                    line = raw_line.strip()
                    if not line:
                        continue
                    yield build_document_record(json.loads(line))
            finally:
                text_reader.detach()


async def import_article_shard(
    shard_path: Path,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    batch_size: int,
) -> ShardImportSummary:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    shard_id = _shard_id(shard_path)
    batch: list[WikipediaDocumentRecord] = []
    records_seen = 0
    records_committed = 0
    batches_committed = 0

    async with session_factory() as session:
        for record in iter_article_records(shard_path):
            batch.append(record)
            records_seen += 1
            if len(batch) >= batch_size:
                await _commit_batch(session, batch)
                records_committed += len(batch)
                batches_committed += 1
                batch.clear()

        if batch:
            await _commit_batch(session, batch)
            records_committed += len(batch)
            batches_committed += 1

    return ShardImportSummary(
        shard_id=shard_id,
        records_seen=records_seen,
        records_committed=records_committed,
        batches_committed=batches_committed,
    )


async def _commit_batch(
    session: AsyncSession,
    batch: list[WikipediaDocumentRecord],
) -> None:
    try:
        await upsert_documents(session, batch)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


def run_import(
    *,
    articles_root: Path,
    state_root: Path,
    workers: int = 3,
    batch_size: int = 1000,
    progress: bool = False,
    limit_shards: int | None = None,
    database_url: str | None = None,
) -> ImportRunResult:
    if workers <= 0:
        raise ValueError("workers must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    _ensure_state_root(state_root)
    lock_handle = _acquire_import_lock(state_root)

    try:
        plan = build_import_plan(
            articles_root=articles_root,
            state_root=state_root,
            limit_shards=limit_shards,
        )

        records_seen = 0
        records_committed = 0
        batches_committed = 0
        completed_shards = plan.completed_shards
        failed_shards = 0
        double_claims = 0
        total_documents = load_total_document_hint(articles_root)
        started_at_monotonic = time.monotonic()
        reporter = build_progress_reporter() if progress else None
        final_status = "completed"

        effective_database_url = database_url or load_settings().database_url
        _write_progress(
            state_root=state_root,
            payload={
                "total_shards": plan.total_shards,
                "completed_shards": completed_shards,
                "failed_shards": failed_shards,
                "running_shards": 0,
                "records_seen": records_seen,
                "records_committed": records_committed,
                "batches_committed": batches_committed,
                "double_claims": double_claims,
                "total_documents": total_documents,
            },
        )
        if reporter is not None:
            reporter(
                build_import_progress_snapshot(
                    total_shards=plan.total_shards,
                    completed_shards=completed_shards,
                    failed_shards=failed_shards,
                    running_shards=0,
                    records_seen=records_seen,
                    records_committed=records_committed,
                    batches_committed=batches_committed,
                    double_claims=double_claims,
                    total_documents=total_documents,
                    started_at_monotonic=started_at_monotonic,
                    status="running",
                )
            )

        try:
            if not plan.shard_paths:
                return ImportRunResult(
                    total_shards=plan.total_shards,
                    completed_shards=completed_shards,
                    failed_shards=failed_shards,
                    double_claims=double_claims,
                    records_seen=records_seen,
                    records_committed=records_committed,
                    batches_committed=batches_committed,
                )

            futures: dict[Future[ShardImportSummary], tuple[Path, str]] = {}
            max_workers = min(workers, len(plan.shard_paths))

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                try:
                    for index, shard_path in enumerate(plan.shard_paths, start=1):
                        worker_id = f"worker-{((index - 1) % max_workers) + 1}"
                        try:
                            _claim_or_reclaim_shard(
                                shard_path,
                                state_root=state_root,
                                worker_id=worker_id,
                            )
                        except FileExistsError:
                            double_claims += 1
                            _append_event(
                                state_root=state_root,
                                event_type="double-claim-skipped",
                                payload={
                                    "shard_id": _shard_id(shard_path),
                                    "worker_id": worker_id,
                                },
                            )
                            continue

                        _append_event(
                            state_root=state_root,
                            event_type="shard-claimed",
                            payload={
                                "shard_id": _shard_id(shard_path),
                                "worker_id": worker_id,
                            },
                        )
                        future = executor.submit(
                            _import_shard_worker,
                            str(shard_path),
                            batch_size,
                            effective_database_url,
                        )
                        futures[future] = (shard_path, worker_id)

                    _write_progress(
                        state_root=state_root,
                        payload={
                            "total_shards": plan.total_shards,
                            "completed_shards": completed_shards,
                            "failed_shards": failed_shards,
                            "running_shards": len(futures),
                            "records_seen": records_seen,
                            "records_committed": records_committed,
                            "batches_committed": batches_committed,
                            "double_claims": double_claims,
                            "total_documents": total_documents,
                        },
                    )
                    if reporter is not None:
                        reporter(
                            build_import_progress_snapshot(
                                total_shards=plan.total_shards,
                                completed_shards=completed_shards,
                                failed_shards=failed_shards,
                                running_shards=len(futures),
                                records_seen=records_seen,
                                records_committed=records_committed,
                                batches_committed=batches_committed,
                                double_claims=double_claims,
                                total_documents=total_documents,
                                started_at_monotonic=started_at_monotonic,
                                status="running",
                            )
                        )

                    for future in as_completed(futures):
                        shard_path, worker_id = futures[future]
                        running_shards = sum(1 for item in futures if not item.done())
                        try:
                            summary = future.result()
                        except Exception as exc:
                            write_failed_marker(
                                shard_path, state_root=state_root, worker_id=worker_id
                            )
                            failed_shards += 1
                            _append_event(
                                state_root=state_root,
                                event_type="shard-failed",
                                payload={
                                    "shard_id": _shard_id(shard_path),
                                    "worker_id": worker_id,
                                    "error": repr(exc),
                                },
                            )
                            _append_failure(
                                state_root=state_root,
                                payload={
                                    "shard_id": _shard_id(shard_path),
                                    "worker_id": worker_id,
                                    "error": repr(exc),
                                },
                            )
                        else:
                            write_completed_marker(
                                shard_path, state_root=state_root, worker_id=worker_id
                            )
                            completed_shards += 1
                            records_seen += summary.records_seen
                            records_committed += summary.records_committed
                            batches_committed += summary.batches_committed
                            _append_event(
                                state_root=state_root,
                                event_type="shard-completed",
                                payload={
                                    "shard_id": summary.shard_id,
                                    "worker_id": worker_id,
                                    "records_committed": summary.records_committed,
                                },
                            )

                        _write_progress(
                            state_root=state_root,
                            payload={
                                "total_shards": plan.total_shards,
                                "completed_shards": completed_shards,
                                "failed_shards": failed_shards,
                                "running_shards": running_shards,
                                "records_seen": records_seen,
                                "records_committed": records_committed,
                                "batches_committed": batches_committed,
                                "double_claims": double_claims,
                                "total_documents": total_documents,
                            },
                        )
                        if reporter is not None:
                            reporter(
                                build_import_progress_snapshot(
                                    total_shards=plan.total_shards,
                                    completed_shards=completed_shards,
                                    failed_shards=failed_shards,
                                    running_shards=running_shards,
                                    records_seen=records_seen,
                                    records_committed=records_committed,
                                    batches_committed=batches_committed,
                                    double_claims=double_claims,
                                    total_documents=total_documents,
                                    started_at_monotonic=started_at_monotonic,
                                    status="running",
                                )
                            )
                except KeyboardInterrupt:
                    final_status = "interrupted"
                    _append_event(
                        state_root=state_root,
                        event_type="import-interrupted",
                        payload={
                            "running_shards": sum(
                                1 for item in futures if not item.done()
                            )
                        },
                    )
                    _interrupt_executor_tree(executor)
                    raise

            return ImportRunResult(
                total_shards=plan.total_shards,
                completed_shards=completed_shards,
                failed_shards=failed_shards,
                double_claims=double_claims,
                records_seen=records_seen,
                records_committed=records_committed,
                batches_committed=batches_committed,
            )
        finally:
            if reporter is not None:
                reporter(
                    build_import_progress_snapshot(
                        total_shards=plan.total_shards,
                        completed_shards=completed_shards,
                        failed_shards=failed_shards,
                        running_shards=0,
                        records_seen=records_seen,
                        records_committed=records_committed,
                        batches_committed=batches_committed,
                        double_claims=double_claims,
                        total_documents=total_documents,
                        started_at_monotonic=started_at_monotonic,
                        status=final_status if failed_shards == 0 else "failed",
                    )
                )
    finally:
        _release_import_lock(lock_handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--articles-root", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--limit-shards", type=int, default=None)
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()

    run_import(
        articles_root=args.articles_root,
        state_root=args.state_root,
        workers=args.workers,
        batch_size=args.batch_size,
        progress=args.progress,
        limit_shards=args.limit_shards,
    )


def _replace_marker(marker: ShardMarker) -> None:
    marker.marker_path.parent.mkdir(parents=True, exist_ok=True)
    for status in ("running", "completed", "failed"):
        existing_path = _marker_path(
            marker.input_path,
            state_root=marker.marker_path.parents[2],
            status=status,
        )
        if existing_path.exists():
            existing_path.unlink()
    marker.marker_path.write_text(
        json.dumps(_marker_payload(marker), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _claim_or_reclaim_shard(
    shard_path: Path,
    *,
    state_root: Path,
    worker_id: str,
) -> ShardMarker:
    if (
        _find_existing_marker(shard_path, state_root=state_root, status="completed")
        is not None
    ):
        raise FileExistsError("completed marker already exists")
    existing_running = _find_existing_marker(
        shard_path, state_root=state_root, status="running"
    )
    existing_failed = _find_existing_marker(
        shard_path, state_root=state_root, status="failed"
    )
    if existing_running is not None or existing_failed is not None:
        return write_running_marker(
            shard_path, state_root=state_root, worker_id=worker_id
        )
    return claim_shard(shard_path, state_root=state_root, worker_id=worker_id)


def _find_existing_marker(
    shard_path: Path, *, state_root: Path, status: ShardStatus
) -> Path | None:
    candidate = _marker_path(shard_path, state_root=state_root, status=status)
    if candidate.exists():
        return candidate
    return None


def _marker_for(
    shard_path: Path,
    *,
    state_root: Path,
    status: ShardStatus,
    worker_id: str,
) -> ShardMarker:
    shard_id = _shard_id(shard_path)
    return ShardMarker(
        shard_id=shard_id,
        input_path=shard_path,
        marker_path=_marker_path(shard_path, state_root=state_root, status=status),
        status=status,
        worker_id=worker_id,
    )


def _marker_path(shard_path: Path, *, state_root: Path, status: ShardStatus) -> Path:
    split_id = shard_path.parent.name
    shard_id = _shard_id(shard_path)
    return state_root / "shards" / split_id / f"{shard_id}.{status}.json"


def _shard_id(shard_path: Path) -> str:
    return shard_path.name.removesuffix(".jsonl.zst")


def _marker_payload(marker: ShardMarker) -> dict[str, str]:
    return {
        "input_path": str(marker.input_path),
        "shard_id": marker.shard_id,
        "status": marker.status,
        "worker_id": marker.worker_id,
    }


def _ensure_state_root(state_root: Path) -> None:
    (state_root / "logs").mkdir(parents=True, exist_ok=True)
    (state_root / "stats").mkdir(parents=True, exist_ok=True)


def _acquire_import_lock(state_root: Path) -> TextIO:
    lock_path = state_root / "import.lock"
    lock_handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lock_handle.close()
        raise RuntimeError(
            f"import already running for state root: {state_root}"
        ) from exc

    lock_handle.seek(0)
    lock_handle.truncate()
    lock_handle.write(
        json.dumps(
            {
                "pid": os.getpid(),
                "acquired_at": time.time(),
            },
            sort_keys=True,
        )
        + "\n"
    )
    lock_handle.flush()
    return lock_handle


def _release_import_lock(lock_handle: TextIO) -> None:
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    finally:
        lock_handle.close()


def _write_progress(*, state_root: Path, payload: dict[str, int | None]) -> None:
    _ensure_state_root(state_root)
    (state_root / "stats" / "progress.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_event(
    *, state_root: Path, event_type: str, payload: dict[str, object]
) -> None:
    _append_jsonl(
        state_root / "logs" / "events.jsonl",
        {"event_type": event_type, **payload},
    )


def _append_failure(*, state_root: Path, payload: dict[str, object]) -> None:
    _append_jsonl(
        state_root / "logs" / "failures.jsonl",
        payload,
    )


def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _interrupt_executor_tree(executor: ProcessPoolExecutor) -> None:
    worker_processes = tuple(
        cast(dict[int, _ProcessHandle], getattr(executor, "_processes", {})).values()
    )
    executor.shutdown(wait=False, cancel_futures=True)
    deadline = time.monotonic() + 1.0
    alive_processes: list[_ProcessHandle] = []

    for process in worker_processes:
        _terminate_process(process)
        _join_process(process, timeout=max(0.0, deadline - time.monotonic()))
        if _is_process_alive(process):
            alive_processes.append(process)

    for process in alive_processes:
        _kill_process(process)
        _join_process(process, timeout=0.5)


def _is_process_alive(process: _ProcessHandle) -> bool:
    try:
        return bool(process.is_alive())
    except ValueError:
        return False


def _terminate_process(process: _ProcessHandle) -> None:
    try:
        process.terminate()
    except ProcessLookupError:
        return


def _kill_process(process: _ProcessHandle) -> None:
    try:
        process.kill()
    except ProcessLookupError:
        return


def _join_process(process: _ProcessHandle, *, timeout: float) -> None:
    process.join(timeout=max(0.0, timeout))


def _import_shard_worker(
    shard_path_str: str,
    batch_size: int,
    database_url: str,
) -> ShardImportSummary:
    return asyncio.run(
        _import_shard_worker_async(
            shard_path=Path(shard_path_str),
            batch_size=batch_size,
            database_url=database_url,
        )
    )


async def _import_shard_worker_async(
    *,
    shard_path: Path,
    batch_size: int,
    database_url: str,
) -> ShardImportSummary:
    session_factory = await _get_worker_session_factory(database_url)
    return await import_article_shard(
        shard_path,
        session_factory=session_factory,
        batch_size=batch_size,
    )


async def _get_worker_session_factory(
    database_url: str,
) -> async_sessionmaker[AsyncSession]:
    global _WORKER_DATABASE_URL, _WORKER_ENGINE, _WORKER_SESSION_FACTORY

    if _WORKER_SESSION_FACTORY is not None and database_url == _WORKER_DATABASE_URL:
        return _WORKER_SESSION_FACTORY

    await _dispose_worker_resources()
    settings = Settings(database_url=database_url)
    engine, session_factory = build_session_factory(settings)
    _WORKER_ENGINE = engine
    _WORKER_SESSION_FACTORY = session_factory
    _WORKER_DATABASE_URL = database_url
    return session_factory


async def _dispose_worker_resources() -> None:
    global _WORKER_DATABASE_URL, _WORKER_ENGINE, _WORKER_SESSION_FACTORY

    if _WORKER_ENGINE is not None:
        await _WORKER_ENGINE.dispose()
    _WORKER_ENGINE = None
    _WORKER_SESSION_FACTORY = None
    _WORKER_DATABASE_URL = None


def _dispose_worker_resources_at_exit() -> None:
    if _WORKER_ENGINE is None:
        return
    asyncio.run(_dispose_worker_resources())


atexit.register(_dispose_worker_resources_at_exit)


if __name__ == "__main__":
    main()
