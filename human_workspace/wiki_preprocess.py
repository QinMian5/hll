"""
Abstract: Controller CLI and run orchestration for the Wikipedia offline preprocessing pipeline.
Out of scope: Wikimedia download automation, full MediaWiki rendering fidelity, and downstream ingestion/index buildout.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import click

from wiki_preprocess_classify import build_redirect_record, classify_page
from wiki_preprocess_clean import clean_wikitext
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
_SPLIT_FILE_RE = re.compile(
    r"^(?:.+-)?pages-articles-multistream-?(?P<split>\d+)\.xml(?:-p\d+p\d+|-\d+)\.bz2$",
)


class ThresholdAbort(RuntimeError):
    """Raised when the configured failure thresholds are exceeded."""

    def __init__(self, trigger: str, diagnostics_path: Path) -> None:
        super().__init__(f"threshold exceeded: {trigger}")
        self.trigger = trigger
        self.diagnostics_path = diagnostics_path


@dataclass(frozen=True, slots=True)
class PipelineResult:
    run_id: str
    run_root: Path
    completed_splits: list[str]
    status: str
    run_stats: dict[str, int]


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


def _split_sort_key(path: Path) -> tuple[int, str]:
    match = _SPLIT_FILE_RE.search(path.name)
    if match is None:
        return (10**9, path.name)
    return (int(match.group("split")), path.name)


def _split_id_from_path(path: Path) -> str:
    match = _SPLIT_FILE_RE.search(path.name)
    if match is None:
        raise ValueError(f"could not derive split id from {path.name}")
    return f"split-{int(match.group('split')):05d}"


def discover_split_inputs(input_root: str | Path) -> list[Path]:
    root = Path(input_root)
    candidates = [
        path
        for path in root.glob("**/*.bz2")
        if _SPLIT_FILE_RE.search(path.name) is not None
    ]
    return sorted(candidates, key=_split_sort_key)


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


def run_pipeline(
    *,
    input_root: str | Path,
    output_root: str | Path,
    source_dump: str,
    shard_max_records: int = DEFAULT_SHARD_MAX_RECORDS,
    shard_max_uncompressed_bytes: int = DEFAULT_SHARD_MAX_UNCOMPRESSED_BYTES,
    thresholds: ThresholdConfig = DEFAULT_THRESHOLDS,
    resume: bool = False,
    clean_page: Callable[[PageExtractionResult], str] | None = None,
) -> PipelineResult:
    input_root_path = Path(input_root)
    output_root_path = Path(output_root)
    split_paths = discover_split_inputs(input_root_path)
    run_root = _select_run_root(output_root_path, resume=resume)
    run_root.mkdir(parents=True, exist_ok=True)
    run_id = run_root.name
    cleaner = clean_page or _default_clean_page

    write_run_manifest(
        run_root,
        RunAuditContext(
            run_id=run_id,
            source_dump=source_dump,
            input_root=input_root_path,
            output_root=output_root_path,
            script_version=SCRIPT_VERSION,
            cleaning_config={"mode": "human-readable"},
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

    for split_path in split_paths:
        split_id = _split_id_from_path(split_path)
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
                    continue
                if classified_page.kind is PageKind.redirect_alias:
                    redirect_writer.write(
                        build_redirect_record(classified_page, source_dump=source_dump)
                    )
                    pages_emitted += 1
                    consecutive_failures = 0
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
        event_logger.write_event(
            event_type="split-completed",
            timestamp=_utc_now(),
            split_id=split_id,
            message=split_path.name,
        )

    write_run_stats(run_root, run_stats)
    event_logger.write_event(
        event_type="run-completed",
        timestamp=_utc_now(),
        message=str(run_root),
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
    resume: bool,
    max_global_failure_ratio: float,
    max_global_failure_count: int,
    max_consecutive_failures: int,
    max_split_failure_ratio: float,
) -> None:
    run_pipeline(
        input_root=input_root,
        output_root=output_root,
        source_dump=source_dump,
        shard_max_records=shard_max_records,
        shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
        resume=resume,
        thresholds=ThresholdConfig(
            max_global_failure_ratio=max_global_failure_ratio,
            max_global_failure_count=max_global_failure_count,
            max_consecutive_failures=max_consecutive_failures,
            max_split_failure_ratio=max_split_failure_ratio,
        ),
    )


if __name__ == "__main__":
    main()
