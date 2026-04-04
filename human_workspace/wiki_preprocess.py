"""
Abstract: Controller CLI and run orchestration for the Wikipedia offline preprocessing pipeline.
Out of scope: Wikimedia download automation, full MediaWiki rendering fidelity, and downstream ingestion/index buildout.
"""

from __future__ import annotations

import json
import queue
import shutil
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime
from multiprocessing import Manager
from pathlib import Path
from typing import Any, Callable

import click

try:
    from rich.console import Console, Group
    from rich.live import Live
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
except ImportError:  # pragma: no cover - exercised only when rich is unavailable.
    Console = None
    Group = None
    Live = None
    Progress = None
    TextColumn = None
    BarColumn = None
    MofNCompleteColumn = None
    TimeElapsedColumn = None
    TimeRemainingColumn = None

from wiki_preprocess_classify import build_redirect_record, classify_page
from wiki_preprocess_clean import clean_wikitext
from wiki_preprocess_index import (
    discover_split_inputs,
    load_index_page_counts,
    parse_split_path,
)
from wiki_preprocess_types import (
    ArticleRecord,
    DisambiguationRecord,
    PageExtractionResult,
    PageKind,
    RunAuditContext,
    SplitManifest,
    SplitStatus,
    ThresholdConfig,
)
from wiki_preprocess_write import (
    StatsTracker,
    build_article_writer,
    build_disambiguation_writer,
    build_failure_logger,
    build_redirect_alias_writer,
    build_run_event_logger,
    build_stats_tracker,
    load_split_manifest,
    load_split_stats,
    write_run_manifest,
    write_run_stats,
    write_split_manifest,
    write_split_stats,
)
from wiki_preprocess_xml import stream_pages

SCRIPT_VERSION = "0.1.0"
DEFAULT_SHARD_MAX_RECORDS = 10_000
DEFAULT_SHARD_MAX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
DEFAULT_THRESHOLDS = ThresholdConfig(
    max_global_failure_ratio=1.0,
    max_global_failure_count=10_000,
    max_consecutive_failures=1_000,
    max_split_failure_ratio=1.0,
)


class ThresholdAbort(RuntimeError):
    """Raised when the configured failure thresholds are exceeded."""

    def __init__(self, trigger: str, diagnostics_path: Path) -> None:
        super().__init__(f"threshold exceeded: {trigger}")
        self.trigger = trigger
        self.diagnostics_path = diagnostics_path


class WorkerAbortRequested(RuntimeError):
    """Raised inside a worker when the parent process requests an early stop."""


@dataclass(frozen=True, slots=True)
class PipelineResult:
    run_id: str
    run_root: Path
    completed_splits: list[str]
    status: str
    run_stats: dict[str, int]


@dataclass(frozen=True, slots=True)
class SplitWorkerResult:
    split_id: str
    pages_seen: int
    pages_emitted: int
    failures: int


class TerminalProgressReporter:
    def __init__(self) -> None:
        self._rendered_lines = 0
        self._last_render_at = 0.0

    def __call__(self, snapshot: dict[str, object]) -> None:
        now = time.monotonic()
        if snapshot.get("status") == "running" and now - self._last_render_at < 0.2:
            return
        self._last_render_at = now
        lines = self._render_lines(snapshot)
        if self._rendered_lines:
            click.echo(f"\x1b[{self._rendered_lines}A", nl=False, err=True)
        for line in lines:
            click.echo(f"\x1b[2K{line}", err=True)
        self._rendered_lines = len(lines)
        if snapshot.get("status") != "running":
            self.close()

    def close(self) -> None:
        if self._rendered_lines:
            click.echo("", err=True)
        self._rendered_lines = 0

    def _render_lines(self, snapshot: dict[str, object]) -> list[str]:
        total_pages = snapshot.get("total_pages")
        processed_pages = int(snapshot.get("processed_pages", 0))
        total_splits = int(snapshot.get("total_splits", 0))
        completed_splits = int(snapshot.get("completed_splits", 0))
        rate = float(snapshot.get("pages_per_second", 0.0))
        active_splits = list(snapshot.get("active_splits", []))

        lines = [
            (
                f"Pages  {self._format_bar(processed_pages, total_pages)} "
                f"{processed_pages}/{total_pages if total_pages is not None else '?'} "
                f"| {rate:.1f} pages/s"
            ),
            (
                f"Splits {self._format_bar(completed_splits, total_splits)} "
                f"{completed_splits}/{total_splits}"
            ),
        ]
        for item in active_splits:
            split_total = item.get("total_pages")
            split_seen = int(item.get("pages_seen", 0))
            lines.append(
                (
                    f"{item['split_id']} "
                    f"{self._format_bar(split_seen, split_total, width=18)} "
                    f"{split_seen}/{split_total if split_total is not None else '?'} "
                    f"emit={item['pages_emitted']} fail={item['failures']}"
                )
            )
        if not active_splits:
            lines.append("No active splits")
        return lines

    def _format_bar(
        self,
        current: int,
        total: object,
        *,
        width: int = 28,
    ) -> str:
        if not isinstance(total, int) or total <= 0:
            return f"[{'#' * min(width, max(1, width // 4))}{'.' * (width - min(width, max(1, width // 4)))}]"
        ratio = max(0.0, min(1.0, current / total))
        filled = int(width * ratio)
        return f"[{'#' * filled}{'.' * (width - filled)}]"


class RichProgressReporter:
    def __init__(self) -> None:
        if Console is None or Group is None or Live is None or Progress is None:
            raise RuntimeError("rich is not available")
        self._console = Console(stderr=True)
        self._summary_progress = Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=28),
            MofNCompleteColumn(),
            TextColumn("{task.fields[details]}"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self._console,
            expand=True,
        )
        self._split_progress = Progress(
            TextColumn("[green]{task.description}"),
            BarColumn(bar_width=18),
            MofNCompleteColumn(),
            TextColumn("emit={task.fields[emitted]}"),
            TextColumn("fail={task.fields[failures]}"),
            console=self._console,
            expand=True,
        )
        self._pages_task_id = self._summary_progress.add_task(
            "Pages",
            total=1,
            completed=0,
            details="0.0 pages/s",
        )
        self._splits_task_id = self._summary_progress.add_task(
            "Splits",
            total=1,
            completed=0,
            details="0 workers",
        )
        self._split_task_ids: dict[str, int] = {}
        self._live = Live(
            Group(self._summary_progress, self._split_progress),
            console=self._console,
            refresh_per_second=10,
            transient=False,
        )
        self._started = False

    def __call__(self, snapshot: dict[str, object]) -> None:
        if not self._started:
            self._live.start()
            self._started = True

        total_pages_value = snapshot.get("total_pages")
        total_pages = (
            int(total_pages_value)
            if isinstance(total_pages_value, int) and total_pages_value > 0
            else max(1, int(snapshot.get("processed_pages", 0)))
        )
        total_splits = max(1, int(snapshot.get("total_splits", 0)))
        processed_pages = int(snapshot.get("processed_pages", 0))
        completed_splits = int(snapshot.get("completed_splits", 0))
        active_splits = list(snapshot.get("active_splits", []))
        rate = float(snapshot.get("pages_per_second", 0.0))

        self._summary_progress.update(
            self._pages_task_id,
            total=total_pages,
            completed=processed_pages,
            details=f"{rate:.1f} pages/s",
        )
        self._summary_progress.update(
            self._splits_task_id,
            total=total_splits,
            completed=completed_splits,
            details=f"{len(active_splits)} active",
        )

        active_ids: set[str] = set()
        for item in active_splits:
            split_id = str(item["split_id"])
            active_ids.add(split_id)
            split_total_value = item.get("total_pages")
            split_total = (
                int(split_total_value)
                if isinstance(split_total_value, int) and split_total_value > 0
                else max(1, int(item.get("pages_seen", 0)))
            )
            task_id = self._split_task_ids.get(split_id)
            if task_id is None:
                task_id = self._split_progress.add_task(
                    split_id,
                    total=split_total,
                    completed=int(item.get("pages_seen", 0)),
                    emitted=int(item.get("pages_emitted", 0)),
                    failures=int(item.get("failures", 0)),
                )
                self._split_task_ids[split_id] = task_id
            else:
                self._split_progress.update(
                    task_id,
                    total=split_total,
                    completed=int(item.get("pages_seen", 0)),
                    emitted=int(item.get("pages_emitted", 0)),
                    failures=int(item.get("failures", 0)),
                )

        for split_id in sorted(set(self._split_task_ids) - active_ids):
            self._split_progress.remove_task(self._split_task_ids.pop(split_id))

        self._live.refresh()
        if snapshot.get("status") not in {"running", "aborting"}:
            self.close()

    def close(self) -> None:
        if self._started:
            self._live.stop()
            self._started = False


def build_progress_reporter() -> TerminalProgressReporter | RichProgressReporter:
    if Console is not None and Group is not None and Live is not None and Progress is not None:
        return RichProgressReporter()
    return TerminalProgressReporter()


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _flatten_run_stats(stats_payload: dict[str, object]) -> dict[str, int]:
    records = dict(stats_payload.get("records", {}))
    return {
        "canonical_articles_emitted": int(records.get("canonical_article", 0)),
        "redirect_aliases_emitted": int(records.get("redirect_alias", 0)),
        "disambiguation_pages_emitted": int(records.get("disambiguation", 0)),
        "ignored_pages": int(records.get("ignored", 0)),
    }


def _snapshot_progress_state(
    *,
    run_id: str,
    run_root: Path,
    status: str,
    workers: int,
    total_splits: int,
    total_pages: int | None,
    split_progress: dict[str, dict[str, object]],
    started_at_monotonic: float,
) -> dict[str, object]:
    processed_pages = sum(
        int(item.get("pages_seen", 0))
        for item in split_progress.values()
    )
    completed_splits = sum(
        1
        for item in split_progress.values()
        if item.get("status") == "completed"
    )
    active_splits = [
        {
            "split_id": split_id,
            "pages_seen": int(item.get("pages_seen", 0)),
            "pages_emitted": int(item.get("pages_emitted", 0)),
            "failures": int(item.get("failures", 0)),
            "total_pages": item.get("total_pages"),
        }
        for split_id, item in sorted(split_progress.items())
        if item.get("status") == "running"
    ]
    elapsed = max(0.001, time.monotonic() - started_at_monotonic)
    return {
        "run_id": run_id,
        "run_root": str(run_root),
        "status": status,
        "workers": workers,
        "total_splits": total_splits,
        "completed_splits": completed_splits,
        "total_pages": total_pages,
        "processed_pages": processed_pages,
        "pages_per_second": processed_pages / elapsed,
        "active_splits": active_splits,
    }


def _emit_progress_snapshot(
    progress_callback: Callable[[dict[str, object]], None] | None,
    snapshot: dict[str, object],
) -> None:
    if progress_callback is not None:
        progress_callback(snapshot)


def _select_run_root(output_root: Path, *, resume: bool) -> Path:
    runs_dir = output_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    existing_runs = sorted(path for path in runs_dir.iterdir() if path.is_dir())
    if resume and existing_runs:
        return existing_runs[-1]
    return runs_dir / f"run-{len(existing_runs) + 1:05d}"


def _safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _reset_interrupted_split(run_root: Path, split_id: str) -> None:
    _safe_rmtree(run_root / "temp" / split_id)
    for artifact_name in ("articles", "redirect_aliases", "disambiguation"):
        _safe_rmtree(run_root / artifact_name / split_id)
    manifest_path = run_root / "manifests" / f"{split_id}.json"
    if manifest_path.exists():
        manifest_path.unlink()
    stats_path = run_root / "stats" / f"{split_id}.json"
    if stats_path.exists():
        stats_path.unlink()


def evaluate_thresholds(
    *,
    consecutive_failures: int,
    split_failure_ratio: float,
    global_failure_ratio: float,
    global_failure_count: int,
    recent_failures: list[dict[str, object]],
    affected_split_id: str,
    logs_root: str | Path,
    thresholds: ThresholdConfig,
) -> None:
    trigger: str | None = None
    if consecutive_failures > thresholds.max_consecutive_failures:
        trigger = "max_consecutive_failures"
    elif split_failure_ratio > thresholds.max_split_failure_ratio:
        trigger = "max_split_failure_ratio"
    elif global_failure_ratio > thresholds.max_global_failure_ratio:
        trigger = "max_global_failure_ratio"
    elif global_failure_count > thresholds.max_global_failure_count:
        trigger = "max_global_failure_count"
    if trigger is None:
        return

    error_distribution = Counter(
        str(failure["error_type"])
        for failure in recent_failures
        if failure.get("error_type") is not None
    )
    logs_path = Path(logs_root)
    logs_path.mkdir(parents=True, exist_ok=True)
    diagnostics_path = logs_path / "threshold_abort.json"
    diagnostics_path.write_text(
        json.dumps(
            {
                "trigger": trigger,
                "affected_split_id": affected_split_id,
                "consecutive_failures": consecutive_failures,
                "split_failure_ratio": split_failure_ratio,
                "global_failure_ratio": global_failure_ratio,
                "global_failure_count": global_failure_count,
                "recent_failures": recent_failures,
                "error_type_distribution": dict(error_distribution),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    raise ThresholdAbort(trigger, diagnostics_path)


def _default_clean_page(page: PageExtractionResult) -> str:
    return clean_wikitext(page.raw_text)


def _load_existing_split_stats(run_root: Path, split_id: str) -> StatsTracker:
    stats_path = run_root / "stats" / f"{split_id}.json"
    if not stats_path.exists():
        return build_stats_tracker()
    return StatsTracker.from_json_dict(load_split_stats(run_root, split_id))


def _update_split_manifest(
    *,
    run_root: Path,
    split_id: str,
    split_path: Path,
    status: SplitStatus,
    pages_seen: int,
    pages_emitted: int,
    failures: int,
    started_at: str,
    finished_at: str | None,
) -> SplitManifest:
    existing_manifest = load_split_manifest(run_root, split_id)
    manifest = SplitManifest(
        split_id=split_id,
        input_file=split_path,
        status=status,
        articles_shards=existing_manifest.articles_shards,
        redirect_aliases_shards=existing_manifest.redirect_aliases_shards,
        disambiguation_shards=existing_manifest.disambiguation_shards,
        pages_seen=pages_seen,
        pages_emitted=pages_emitted,
        failures=failures,
        started_at=started_at,
        finished_at=finished_at,
    )
    write_split_manifest(run_root, manifest)
    return manifest


def _evaluate_local_thresholds(
    *,
    consecutive_failures: int,
    split_failure_ratio: float,
    recent_failures: list[dict[str, object]],
    affected_split_id: str,
    logs_root: str | Path,
    thresholds: ThresholdConfig,
) -> None:
    evaluate_thresholds(
        consecutive_failures=consecutive_failures,
        split_failure_ratio=split_failure_ratio,
        global_failure_ratio=0.0,
        global_failure_count=0,
        recent_failures=recent_failures,
        affected_split_id=affected_split_id,
        logs_root=logs_root,
        thresholds=ThresholdConfig(
            max_global_failure_ratio=1.0,
            max_global_failure_count=10**12,
            max_consecutive_failures=thresholds.max_consecutive_failures,
            max_split_failure_ratio=thresholds.max_split_failure_ratio,
        ),
    )


def _process_split_worker(
    *,
    run_root: str | Path,
    split_path: str | Path,
    source_dump: str,
    shard_max_records: int,
    shard_max_uncompressed_bytes: int,
    thresholds: ThresholdConfig,
    split_total_pages: int | None,
    progress_queue: Any | None,
    abort_event: Any | None,
    progress_interval_pages: int = 250,
) -> SplitWorkerResult:
    run_root_path = Path(run_root)
    split_path = Path(split_path)
    split_info = parse_split_path(split_path)
    split_id = split_info.split_id
    split_started_at = _utc_now()
    write_split_manifest(
        run_root_path,
        SplitManifest(
            split_id=split_id,
            input_file=split_path,
            status=SplitStatus.running,
            started_at=split_started_at,
        ),
    )

    article_writer = build_article_writer(
        run_root=run_root_path,
        split_id=split_id,
        input_file=split_path,
        shard_max_records=shard_max_records,
        shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
    )
    redirect_writer = build_redirect_alias_writer(
        run_root=run_root_path,
        split_id=split_id,
        input_file=split_path,
        shard_max_records=shard_max_records,
        shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
    )
    disambiguation_writer = build_disambiguation_writer(
        run_root=run_root_path,
        split_id=split_id,
        input_file=split_path,
        shard_max_records=shard_max_records,
        shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
    )
    controller_split_stats = build_stats_tracker()
    pages_seen = 0
    pages_emitted = 0
    split_failures = 0
    consecutive_failures = 0
    recent_failures: list[dict[str, object]] = []
    last_progress_pages = 0

    def emit_message(
        message_type: str,
        *,
        status: str,
        failure: dict[str, object] | None = None,
    ) -> None:
        if progress_queue is None:
            return
        payload = {
            "message_type": message_type,
            "split_id": split_id,
            "status": status,
            "pages_seen": pages_seen,
            "pages_emitted": pages_emitted,
            "failures": split_failures,
            "total_pages": split_total_pages,
        }
        if failure is not None:
            payload["failure"] = failure
        progress_queue.put(payload)

    def emit_progress(status: str) -> None:
        emit_message("progress", status=status)

    def handle_page_failure(
        error: Exception,
        context: dict[str, object],
        *,
        stage: str,
        count_page: bool,
    ) -> None:
        nonlocal pages_seen, split_failures, consecutive_failures
        if count_page:
            pages_seen += 1
        split_failures += 1
        consecutive_failures += 1
        controller_split_stats.record_failure(type(error).__name__)
        page_id = context.get("page_id")
        parsed_page_id = int(page_id) if isinstance(page_id, str) and page_id.isdigit() else None
        title = context.get("title")
        title_text = title if isinstance(title, str) and title else None
        failure_payload = {
            "split_id": split_id,
            "page_id": parsed_page_id,
            "title": title_text,
            "stage": stage,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": _utc_now(),
        }
        recent_failures.append(
            {
                "page_id": parsed_page_id,
                "title": title_text,
                "stage": stage,
                "error_type": type(error).__name__,
            }
        )
        del recent_failures[:-10]
        emit_message("failure", status="running", failure=failure_payload)
        _evaluate_local_thresholds(
            consecutive_failures=consecutive_failures,
            split_failure_ratio=split_failures / max(1, pages_seen),
            recent_failures=recent_failures,
            affected_split_id=split_id,
            logs_root=run_root_path / "logs",
            thresholds=thresholds,
        )

    emit_progress("running")

    try:
        for page in stream_pages(
            split_path,
            source_dump=source_dump,
            on_page_error=lambda error, context: handle_page_failure(
                error,
                context,
                stage="xml_parse",
                count_page=True,
            ),
        ):
            if abort_event is not None and abort_event.is_set():
                raise WorkerAbortRequested(split_id)
            pages_seen += 1
            classified_page = classify_page(page)
            if classified_page.kind is PageKind.ignored:
                controller_split_stats.record_ignored()
                consecutive_failures = 0
            elif classified_page.kind is PageKind.redirect_alias:
                redirect_writer.write(
                    build_redirect_record(classified_page, source_dump=source_dump)
                )
                pages_emitted += 1
                consecutive_failures = 0
            elif classified_page.kind is PageKind.disambiguation:
                disambiguation_writer.write(
                    DisambiguationRecord(
                        page_id=classified_page.page_id,
                        title=classified_page.title,
                        source_url=classified_page.source_url,
                    )
                )
                pages_emitted += 1
                consecutive_failures = 0
            else:
                try:
                    cleaned_text = clean_wikitext(classified_page.raw_text)
                except Exception as error:
                    handle_page_failure(
                        error,
                        {
                            "page_id": str(classified_page.page_id),
                            "title": classified_page.title,
                        },
                        stage="cleaning",
                        count_page=False,
                    )
                else:
                    article_writer.write(
                        ArticleRecord(
                            page_id=classified_page.page_id,
                            title=classified_page.title,
                            revision_id=classified_page.revision_id,
                            revision_timestamp=classified_page.revision_timestamp,
                            source_dump=classified_page.source_dump,
                            source_url=classified_page.source_url,
                            clean_text=cleaned_text,
                            text_length=len(cleaned_text),
                        )
                    )
                    pages_emitted += 1
                    consecutive_failures = 0
            if pages_seen - last_progress_pages >= progress_interval_pages:
                emit_progress("running")
                last_progress_pages = pages_seen
    except ThresholdAbort:
        write_split_manifest(
            run_root_path,
            SplitManifest(
                split_id=split_id,
                input_file=split_path,
                status=SplitStatus.failed_threshold,
                pages_seen=pages_seen,
                pages_emitted=pages_emitted,
                failures=split_failures,
                started_at=split_started_at,
                finished_at=_utc_now(),
            ),
        )
        emit_progress("failed-threshold")
        raise

    article_writer.close()
    redirect_writer.close()
    disambiguation_writer.close()

    split_stats = _load_existing_split_stats(run_root_path, split_id)
    split_stats.merge(controller_split_stats)
    write_split_stats(run_root_path, split_id, split_stats)
    _update_split_manifest(
        run_root=run_root_path,
        split_id=split_id,
        split_path=split_path,
        status=SplitStatus.completed,
        pages_seen=pages_seen,
        pages_emitted=pages_emitted,
        failures=split_failures,
        started_at=split_started_at,
        finished_at=_utc_now(),
    )
    emit_progress("completed")
    return SplitWorkerResult(
        split_id=split_id,
        pages_seen=pages_seen,
        pages_emitted=pages_emitted,
        failures=split_failures,
    )


def _run_pipeline_parallel(
    *,
    input_root: Path,
    output_root: Path,
    source_dump: str,
    shard_max_records: int,
    shard_max_uncompressed_bytes: int,
    thresholds: ThresholdConfig,
    workers: int,
    resume: bool,
    progress_callback: Callable[[dict[str, object]], None] | None,
) -> PipelineResult:
    split_paths = discover_split_inputs(input_root)
    split_page_counts = load_index_page_counts(input_root)
    total_pages = sum(split_page_counts.values()) if split_page_counts else None
    run_root = _select_run_root(output_root, resume=resume)
    run_root.mkdir(parents=True, exist_ok=True)
    run_id = run_root.name

    write_run_manifest(
        run_root,
        RunAuditContext(
            run_id=run_id,
            source_dump=source_dump,
            input_root=input_root,
            output_root=output_root,
            script_version=SCRIPT_VERSION,
            cleaning_config={"mode": "human-readable", "workers": workers},
            split_count=len(split_paths),
        ),
    )

    failure_logger = build_failure_logger(run_root, run_id=run_id)
    event_logger = build_run_event_logger(run_root, run_id=run_id)
    run_stats = build_stats_tracker()
    completed_splits: list[str] = []
    split_progress: dict[str, dict[str, object]] = {}
    global_failures = 0
    recent_failures: list[dict[str, object]] = []
    started_at_monotonic = time.monotonic()
    _emit_progress_snapshot(
        progress_callback,
        _snapshot_progress_state(
            run_id=run_id,
            run_root=run_root,
            status="running",
            workers=workers,
            total_splits=len(split_paths),
            total_pages=total_pages,
            split_progress=split_progress,
            started_at_monotonic=started_at_monotonic,
        ),
    )

    with Manager() as manager, ProcessPoolExecutor(max_workers=workers) as executor:
        progress_queue = manager.Queue()
        abort_event = manager.Event()
        future_to_split_id = {}
        abort_error: Exception | None = None

        def process_worker_message(message: dict[str, object]) -> None:
            nonlocal global_failures, abort_error
            split_id = str(message["split_id"])
            split_progress[split_id] = {
                "split_id": split_id,
                "status": str(message["status"]),
                "pages_seen": int(message["pages_seen"]),
                "pages_emitted": int(message["pages_emitted"]),
                "failures": int(message["failures"]),
                "total_pages": message.get("total_pages"),
            }

            if message.get("message_type") == "failure":
                failure = dict(message["failure"])
                failure_logger.write_failure(
                    split_id=split_id,
                    page_id=failure.get("page_id"),  # type: ignore[arg-type]
                    title=failure.get("title"),  # type: ignore[arg-type]
                    stage=str(failure["stage"]),
                    error_type=str(failure["error_type"]),
                    error_message=str(failure["error_message"]),
                    timestamp=str(failure["timestamp"]),
                )
                global_failures += 1
                recent_failures.append(
                    {
                        "page_id": failure.get("page_id"),
                        "title": failure.get("title"),
                        "stage": failure.get("stage"),
                        "error_type": failure.get("error_type"),
                    }
                )
                del recent_failures[:-10]
                if abort_error is None:
                    try:
                        evaluate_thresholds(
                            consecutive_failures=0,
                            split_failure_ratio=int(message["failures"]) / max(1, int(message["pages_seen"])),
                            global_failure_ratio=global_failures / max(
                                1,
                                sum(
                                    int(item.get("pages_seen", 0))
                                    for item in split_progress.values()
                                ),
                            ),
                            global_failure_count=global_failures,
                            recent_failures=recent_failures,
                            affected_split_id=split_id,
                            logs_root=run_root / "logs",
                            thresholds=ThresholdConfig(
                                max_global_failure_ratio=thresholds.max_global_failure_ratio,
                                max_global_failure_count=thresholds.max_global_failure_count,
                                max_consecutive_failures=10**12,
                                max_split_failure_ratio=thresholds.max_split_failure_ratio,
                            ),
                        )
                    except ThresholdAbort as error:
                        abort_error = error
                        abort_event.set()
                        event_logger.write_event(
                            event_type="run-aborting",
                            timestamp=_utc_now(),
                            split_id=split_id,
                            message=error.trigger,
                        )

            _emit_progress_snapshot(
                progress_callback,
                _snapshot_progress_state(
                    run_id=run_id,
                    run_root=run_root,
                    status="running" if abort_error is None else "aborting",
                    workers=workers,
                    total_splits=len(split_paths),
                    total_pages=total_pages,
                    split_progress=split_progress,
                    started_at_monotonic=started_at_monotonic,
                ),
            )

        for split_path in split_paths:
            split_id = parse_split_path(split_path).split_id
            manifest_path = run_root / "manifests" / f"{split_id}.json"
            if manifest_path.exists():
                existing_manifest = load_split_manifest(run_root, split_id)
                if resume and existing_manifest.status is SplitStatus.completed:
                    run_stats.merge(_load_existing_split_stats(run_root, split_id))
                    completed_splits.append(split_id)
                    split_progress[split_id] = {
                        "split_id": split_id,
                        "status": "completed",
                        "pages_seen": existing_manifest.pages_seen,
                        "pages_emitted": existing_manifest.pages_emitted,
                        "failures": existing_manifest.failures,
                        "total_pages": split_page_counts.get(split_id),
                    }
                    continue
                if resume and existing_manifest.status in {
                    SplitStatus.running,
                    SplitStatus.failed_threshold,
                }:
                    _reset_interrupted_split(run_root, split_id)
            event_logger.write_event(
                event_type="split-started",
                timestamp=_utc_now(),
                split_id=split_id,
                message=split_path.name,
            )
            future = executor.submit(
                _process_split_worker,
                run_root=run_root,
                split_path=split_path,
                source_dump=source_dump,
                shard_max_records=shard_max_records,
                shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
                thresholds=thresholds,
                split_total_pages=split_page_counts.get(split_id),
                progress_queue=progress_queue,
                abort_event=abort_event,
            )
            future_to_split_id[future] = split_id

        pending = set(future_to_split_id)
        while pending:
            done, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
            while True:
                try:
                    message = progress_queue.get_nowait()
                except queue.Empty:
                    break
                process_worker_message(dict(message))

            for future in done:
                split_id = future_to_split_id[future]
                try:
                    result = future.result()
                except WorkerAbortRequested:
                    continue
                except ThresholdAbort as error:
                    if abort_error is None:
                        abort_error = error
                        abort_event.set()
                        event_logger.write_event(
                            event_type="run-aborting",
                            timestamp=_utc_now(),
                            split_id=split_id,
                            message=error.trigger,
                        )
                    continue
                except Exception as error:
                    if abort_error is None:
                        abort_error = error
                        abort_event.set()
                        event_logger.write_event(
                            event_type="run-aborting",
                            timestamp=_utc_now(),
                            split_id=split_id,
                            message=type(error).__name__,
                        )
                    continue

                split_stats = _load_existing_split_stats(run_root, split_id)
                run_stats.merge(split_stats)
                completed_splits.append(split_id)
                event_logger.write_event(
                    event_type="split-completed",
                    timestamp=_utc_now(),
                    split_id=split_id,
                    message=str(result.pages_emitted),
                )

        while True:
            try:
                message = progress_queue.get_nowait()
            except queue.Empty:
                break
            process_worker_message(dict(message))

    if abort_error is not None:
        write_run_stats(run_root, run_stats)
        _emit_progress_snapshot(
            progress_callback,
            _snapshot_progress_state(
                run_id=run_id,
                run_root=run_root,
                status="failed-threshold" if isinstance(abort_error, ThresholdAbort) else "failed",
                workers=workers,
                total_splits=len(split_paths),
                total_pages=total_pages,
                split_progress=split_progress,
                started_at_monotonic=started_at_monotonic,
            ),
        )
        raise abort_error

    write_run_stats(run_root, run_stats)
    event_logger.write_event(
        event_type="run-completed",
        timestamp=_utc_now(),
        message=str(run_root),
    )
    _emit_progress_snapshot(
        progress_callback,
        _snapshot_progress_state(
            run_id=run_id,
            run_root=run_root,
            status="completed",
            workers=workers,
            total_splits=len(split_paths),
            total_pages=total_pages,
            split_progress=split_progress,
            started_at_monotonic=started_at_monotonic,
        ),
    )
    run_stats_payload = run_stats.to_json_dict()
    return PipelineResult(
        run_id=run_id,
        run_root=run_root,
        completed_splits=sorted(completed_splits),
        status="completed",
        run_stats=_flatten_run_stats(run_stats_payload),
    )


def run_pipeline(
    *,
    input_root: str | Path,
    output_root: str | Path,
    source_dump: str,
    shard_max_records: int = DEFAULT_SHARD_MAX_RECORDS,
    shard_max_uncompressed_bytes: int = DEFAULT_SHARD_MAX_UNCOMPRESSED_BYTES,
    thresholds: ThresholdConfig = DEFAULT_THRESHOLDS,
    resume: bool = False,
    workers: int = 1,
    clean_page: Callable[[PageExtractionResult], str] | None = None,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
) -> PipelineResult:
    input_root_path = Path(input_root)
    output_root_path = Path(output_root)
    if workers > 1:
        if clean_page is not None:
            raise ValueError("custom clean_page callbacks are not supported when workers > 1")
        return _run_pipeline_parallel(
            input_root=input_root_path,
            output_root=output_root_path,
            source_dump=source_dump,
            shard_max_records=shard_max_records,
            shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
            thresholds=thresholds,
            workers=workers,
            resume=resume,
            progress_callback=progress_callback,
        )
    split_paths = discover_split_inputs(input_root_path)
    split_page_counts = load_index_page_counts(input_root_path)
    total_pages = sum(split_page_counts.values()) if split_page_counts else None
    run_root = _select_run_root(output_root_path, resume=resume)
    run_root.mkdir(parents=True, exist_ok=True)
    run_id = run_root.name
    cleaner = clean_page or _default_clean_page
    started_at_monotonic = time.monotonic()
    split_progress: dict[str, dict[str, object]] = {}

    write_run_manifest(
        run_root,
        RunAuditContext(
            run_id=run_id,
            source_dump=source_dump,
            input_root=input_root_path,
            output_root=output_root_path,
            script_version=SCRIPT_VERSION,
            cleaning_config={"mode": "human-readable", "workers": workers},
            split_count=len(split_paths),
        ),
    )

    failure_logger = build_failure_logger(run_root, run_id=run_id)
    event_logger = build_run_event_logger(run_root, run_id=run_id)
    run_stats = build_stats_tracker()
    completed_splits: list[str] = []
    global_failures = 0
    consecutive_failures = 0
    recent_failures: list[dict[str, object]] = []
    total_pages_seen = 0
    _emit_progress_snapshot(
        progress_callback,
        _snapshot_progress_state(
            run_id=run_id,
            run_root=run_root,
            status="running",
            workers=workers,
            total_splits=len(split_paths),
            total_pages=total_pages,
            split_progress=split_progress,
            started_at_monotonic=started_at_monotonic,
        ),
    )

    for split_path in split_paths:
        split_id = parse_split_path(split_path).split_id
        manifest_path = run_root / "manifests" / f"{split_id}.json"
        existing_manifest = None
        if manifest_path.exists():
            existing_manifest = load_split_manifest(run_root, split_id)
            if resume and existing_manifest.status is SplitStatus.completed:
                run_stats.merge(_load_existing_split_stats(run_root, split_id))
                completed_splits.append(split_id)
                continue
            if resume and existing_manifest.status in {
                SplitStatus.running,
                SplitStatus.failed_threshold,
            }:
                _reset_interrupted_split(run_root, split_id)
                existing_manifest = None

        split_started_at = _utc_now()
        write_split_manifest(
            run_root,
            SplitManifest(
                split_id=split_id,
                input_file=split_path,
                status=SplitStatus.running,
                started_at=split_started_at,
            ),
        )
        event_logger.write_event(
            event_type="split-started",
            timestamp=split_started_at,
            split_id=split_id,
            message=split_path.name,
        )

        article_writer = build_article_writer(
            run_root=run_root,
            split_id=split_id,
            input_file=split_path,
            shard_max_records=shard_max_records,
            shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
        )
        redirect_writer = build_redirect_alias_writer(
            run_root=run_root,
            split_id=split_id,
            input_file=split_path,
            shard_max_records=shard_max_records,
            shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
        )
        disambiguation_writer = build_disambiguation_writer(
            run_root=run_root,
            split_id=split_id,
            input_file=split_path,
            shard_max_records=shard_max_records,
            shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
        )
        controller_split_stats = build_stats_tracker()
        pages_seen = 0
        pages_emitted = 0
        split_failures = 0
        split_progress[split_id] = {
            "split_id": split_id,
            "status": "running",
            "pages_seen": 0,
            "pages_emitted": 0,
            "failures": 0,
            "total_pages": split_page_counts.get(split_id),
        }
        _emit_progress_snapshot(
            progress_callback,
            _snapshot_progress_state(
                run_id=run_id,
                run_root=run_root,
                status="running",
                workers=workers,
                total_splits=len(split_paths),
                total_pages=total_pages,
                split_progress=split_progress,
                started_at_monotonic=started_at_monotonic,
            ),
        )

        def handle_page_failure(
            error: Exception,
            context: dict[str, object],
            *,
            stage: str,
            count_page: bool,
        ) -> None:
            nonlocal pages_seen, split_failures, global_failures, consecutive_failures, total_pages_seen
            if count_page:
                pages_seen += 1
                total_pages_seen += 1
            split_failures += 1
            global_failures += 1
            consecutive_failures += 1
            controller_split_stats.record_failure(type(error).__name__)
            page_id = context.get("page_id")
            parsed_page_id = int(page_id) if isinstance(page_id, str) and page_id.isdigit() else None
            title = context.get("title")
            title_text = title if isinstance(title, str) and title else None
            timestamp = _utc_now()
            failure_logger.write_failure(
                split_id=split_id,
                page_id=parsed_page_id,
                title=title_text,
                stage=stage,
                error_type=type(error).__name__,
                error_message=str(error),
                timestamp=timestamp,
            )
            recent_failures.append(
                {
                    "page_id": parsed_page_id,
                    "title": title_text,
                    "stage": stage,
                    "error_type": type(error).__name__,
                }
            )
            del recent_failures[:-10]
            evaluate_thresholds(
                consecutive_failures=consecutive_failures,
                split_failure_ratio=split_failures / pages_seen,
                global_failure_ratio=global_failures / max(1, total_pages_seen),
                global_failure_count=global_failures,
                recent_failures=recent_failures,
                affected_split_id=split_id,
                logs_root=run_root / "logs",
                thresholds=thresholds,
            )
            split_progress[split_id] = {
                "split_id": split_id,
                "status": "running",
                "pages_seen": pages_seen,
                "pages_emitted": pages_emitted,
                "failures": split_failures,
                "total_pages": split_page_counts.get(split_id),
            }
            _emit_progress_snapshot(
                progress_callback,
                _snapshot_progress_state(
                    run_id=run_id,
                    run_root=run_root,
                    status="running",
                    workers=workers,
                    total_splits=len(split_paths),
                    total_pages=total_pages,
                    split_progress=split_progress,
                    started_at_monotonic=started_at_monotonic,
                ),
            )

        try:
            for page in stream_pages(
                split_path,
                source_dump=source_dump,
                on_page_error=lambda error, context: handle_page_failure(
                    error,
                    context,
                    stage="xml_parse",
                    count_page=True,
                ),
            ):
                pages_seen += 1
                total_pages_seen += 1
                classified_page = classify_page(page)
                if classified_page.kind is PageKind.ignored:
                    controller_split_stats.record_ignored()
                    consecutive_failures = 0
                    split_progress[split_id]["pages_seen"] = pages_seen
                    continue
                if classified_page.kind is PageKind.redirect_alias:
                    redirect_writer.write(
                        build_redirect_record(classified_page, source_dump=source_dump)
                    )
                    pages_emitted += 1
                    consecutive_failures = 0
                    split_progress[split_id]["pages_seen"] = pages_seen
                    split_progress[split_id]["pages_emitted"] = pages_emitted
                    continue
                if classified_page.kind is PageKind.disambiguation:
                    disambiguation_writer.write(
                        DisambiguationRecord(
                            page_id=classified_page.page_id,
                            title=classified_page.title,
                            source_url=classified_page.source_url,
                        )
                    )
                    pages_emitted += 1
                    consecutive_failures = 0
                    split_progress[split_id]["pages_seen"] = pages_seen
                    split_progress[split_id]["pages_emitted"] = pages_emitted
                    continue
                try:
                    cleaned_text = cleaner(classified_page)
                except Exception as error:
                    handle_page_failure(
                        error,
                        {
                            "page_id": str(classified_page.page_id),
                            "title": classified_page.title,
                        },
                        stage="cleaning",
                        count_page=False,
                    )
                    continue
                article_writer.write(
                    ArticleRecord(
                        page_id=classified_page.page_id,
                        title=classified_page.title,
                        revision_id=classified_page.revision_id,
                        revision_timestamp=classified_page.revision_timestamp,
                        source_dump=classified_page.source_dump,
                        source_url=classified_page.source_url,
                        clean_text=cleaned_text,
                        text_length=len(cleaned_text),
                    )
                )
                pages_emitted += 1
                consecutive_failures = 0
                split_progress[split_id]["pages_seen"] = pages_seen
                split_progress[split_id]["pages_emitted"] = pages_emitted
        except ThresholdAbort:
            write_split_manifest(
                run_root,
                SplitManifest(
                    split_id=split_id,
                    input_file=split_path,
                    status=SplitStatus.failed_threshold,
                    pages_seen=pages_seen,
                    pages_emitted=pages_emitted,
                    failures=split_failures,
                    started_at=split_started_at,
                    finished_at=_utc_now(),
                ),
            )
            raise

        article_writer.close()
        redirect_writer.close()
        disambiguation_writer.close()

        split_stats = _load_existing_split_stats(run_root, split_id)
        split_stats.merge(controller_split_stats)
        write_split_stats(run_root, split_id, split_stats)
        _update_split_manifest(
            run_root=run_root,
            split_id=split_id,
            split_path=split_path,
            status=SplitStatus.completed,
            pages_seen=pages_seen,
            pages_emitted=pages_emitted,
            failures=split_failures,
            started_at=split_started_at,
            finished_at=_utc_now(),
        )
        run_stats.merge(split_stats)
        completed_splits.append(split_id)
        split_progress[split_id] = {
            "split_id": split_id,
            "status": "completed",
            "pages_seen": pages_seen,
            "pages_emitted": pages_emitted,
            "failures": split_failures,
            "total_pages": split_page_counts.get(split_id),
        }
        event_logger.write_event(
            event_type="split-completed",
            timestamp=_utc_now(),
            split_id=split_id,
            message=split_path.name,
        )
        _emit_progress_snapshot(
            progress_callback,
            _snapshot_progress_state(
                run_id=run_id,
                run_root=run_root,
                status="running",
                workers=workers,
                total_splits=len(split_paths),
                total_pages=total_pages,
                split_progress=split_progress,
                started_at_monotonic=started_at_monotonic,
            ),
        )

    write_run_stats(run_root, run_stats)
    event_logger.write_event(
        event_type="run-completed",
        timestamp=_utc_now(),
        message=str(run_root),
    )
    _emit_progress_snapshot(
        progress_callback,
        _snapshot_progress_state(
            run_id=run_id,
            run_root=run_root,
            status="completed",
            workers=workers,
            total_splits=len(split_paths),
            total_pages=total_pages,
            split_progress=split_progress,
            started_at_monotonic=started_at_monotonic,
        ),
    )
    run_stats_payload = run_stats.to_json_dict()
    return PipelineResult(
        run_id=run_id,
        run_root=run_root,
        completed_splits=completed_splits,
        status="completed",
        run_stats=_flatten_run_stats(run_stats_payload),
    )


@click.command()
@click.option("--input-root", type=click.Path(path_type=Path, exists=True, file_okay=False), required=True)
@click.option("--output-root", type=click.Path(path_type=Path, file_okay=False), required=True)
@click.option("--source-dump", required=True)
@click.option("--shard-max-records", default=DEFAULT_SHARD_MAX_RECORDS, show_default=True, type=click.IntRange(min=1))
@click.option(
    "--shard-max-uncompressed-bytes",
    default=DEFAULT_SHARD_MAX_UNCOMPRESSED_BYTES,
    show_default=True,
    type=click.IntRange(min=1),
)
@click.option("--workers", default=1, show_default=True, type=click.IntRange(min=1))
@click.option("--progress/--no-progress", default=False, show_default=True)
@click.option("--resume", is_flag=True, help="Resume the latest interrupted run.")
@click.option(
    "--max-global-failure-ratio",
    default=DEFAULT_THRESHOLDS.max_global_failure_ratio,
    show_default=True,
    type=click.FloatRange(min=0.0, max=1.0),
)
@click.option(
    "--max-global-failure-count",
    default=DEFAULT_THRESHOLDS.max_global_failure_count,
    show_default=True,
    type=click.IntRange(min=0),
)
@click.option(
    "--max-consecutive-failures",
    default=DEFAULT_THRESHOLDS.max_consecutive_failures,
    show_default=True,
    type=click.IntRange(min=1),
)
@click.option(
    "--max-split-failure-ratio",
    default=DEFAULT_THRESHOLDS.max_split_failure_ratio,
    show_default=True,
    type=click.FloatRange(min=0.0, max=1.0),
)
def main(
    *,
    input_root: Path,
    output_root: Path,
    source_dump: str,
    shard_max_records: int,
    shard_max_uncompressed_bytes: int,
    workers: int,
    progress: bool,
    resume: bool,
    max_global_failure_ratio: float,
    max_global_failure_count: int,
    max_consecutive_failures: int,
    max_split_failure_ratio: float,
) -> None:
    reporter = build_progress_reporter() if progress else None
    try:
        run_pipeline(
            input_root=input_root,
            output_root=output_root,
            source_dump=source_dump,
            shard_max_records=shard_max_records,
            shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
            workers=workers,
            resume=resume,
            progress_callback=reporter,
            thresholds=ThresholdConfig(
                max_global_failure_ratio=max_global_failure_ratio,
                max_global_failure_count=max_global_failure_count,
                max_consecutive_failures=max_consecutive_failures,
                max_split_failure_ratio=max_split_failure_ratio,
            ),
        )
    finally:
        if reporter is not None:
            reporter.close()


if __name__ == "__main__":
    main()
