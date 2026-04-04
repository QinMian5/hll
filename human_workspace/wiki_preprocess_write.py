"""
Abstract: Deterministic artifact writers, manifests, stats, and log helpers for Wikipedia preprocessing runs.
Out of scope: XML extraction, page classification, clean-text generation, and CLI orchestration.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Protocol

import zstandard as zstd

from wiki_preprocess_types import (
    ArticleRecord,
    DisambiguationRecord,
    FailureEvent,
    RedirectAliasRecord,
    RunAuditContext,
    SplitManifest,
    SplitStatus,
)


class JsonRecord(Protocol):
    def to_json_dict(self) -> dict[str, object]:
        """Return the ordered JSON payload for a persisted record."""


def articles_dir(run_root: str | Path) -> Path:
    return Path(run_root) / "articles"


def redirect_aliases_dir(run_root: str | Path) -> Path:
    return Path(run_root) / "redirect_aliases"


def disambiguation_dir(run_root: str | Path) -> Path:
    return Path(run_root) / "disambiguation"


def manifests_dir(run_root: str | Path) -> Path:
    return Path(run_root) / "manifests"


def stats_dir(run_root: str | Path) -> Path:
    return Path(run_root) / "stats"


def logs_dir(run_root: str | Path) -> Path:
    return Path(run_root) / "logs"


def temp_dir(run_root: str | Path) -> Path:
    return Path(run_root) / "temp"


def run_manifest_path(run_root: str | Path) -> Path:
    return manifests_dir(run_root) / "run.json"


def split_manifest_path(run_root: str | Path, split_id: str) -> Path:
    return manifests_dir(run_root) / f"{split_id}.json"


def split_stats_path(run_root: str | Path, split_id: str) -> Path:
    return stats_dir(run_root) / f"{split_id}.json"


def parse_failures_log_path(run_root: str | Path) -> Path:
    return logs_dir(run_root) / "parse_failures.jsonl"


def run_events_log_path(run_root: str | Path) -> Path:
    return logs_dir(run_root) / "run_events.jsonl"


def _temp_output_path(run_root: Path, relative_path: Path) -> Path:
    return temp_dir(run_root) / relative_path.parent / f"{relative_path.name}.tmp"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_atomic_bytes(run_root: Path, relative_path: Path, payload: bytes) -> Path:
    final_path = run_root / relative_path
    temp_path = _temp_output_path(run_root, relative_path)
    _ensure_parent(temp_path)
    _ensure_parent(final_path)
    temp_path.write_bytes(payload)
    os.replace(temp_path, final_path)
    return final_path


def _write_atomic_json(run_root: Path, relative_path: Path, payload: dict[str, object]) -> Path:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return _write_atomic_bytes(run_root, relative_path, data)


class StatsTracker:
    def __init__(self) -> None:
        self._record_counts: dict[str, int] = {
            "canonical_article": 0,
            "redirect_alias": 0,
            "disambiguation": 0,
            "ignored": 0,
        }
        self._failure_types: Counter[str] = Counter()
        self._shard_counts: dict[str, int] = {
            "articles": 0,
            "redirect_aliases": 0,
            "disambiguation": 0,
        }
        self._text_length_count = 0
        self._text_length_sum = 0
        self._text_length_min: int | None = None
        self._text_length_max: int | None = None

    def record_article(self, text_length: int) -> None:
        self._record_counts["canonical_article"] += 1
        self._text_length_count += 1
        self._text_length_sum += text_length
        if self._text_length_min is None or text_length < self._text_length_min:
            self._text_length_min = text_length
        if self._text_length_max is None or text_length > self._text_length_max:
            self._text_length_max = text_length

    def record_redirect_alias(self) -> None:
        self._record_counts["redirect_alias"] += 1

    def record_disambiguation(self) -> None:
        self._record_counts["disambiguation"] += 1

    def record_failure(self, error_type: str) -> None:
        self._failure_types[error_type] += 1

    def record_shard(self, artifact_kind: str) -> None:
        self._shard_counts[artifact_kind] += 1

    def merge(self, other: "StatsTracker") -> None:
        for key, value in other._record_counts.items():
            self._record_counts[key] += value
        self._failure_types.update(other._failure_types)
        for key, value in other._shard_counts.items():
            self._shard_counts[key] += value
        if other._text_length_count:
            self._text_length_count += other._text_length_count
            self._text_length_sum += other._text_length_sum
            if self._text_length_min is None or (
                other._text_length_min is not None
                and other._text_length_min < self._text_length_min
            ):
                self._text_length_min = other._text_length_min
            if self._text_length_max is None or (
                other._text_length_max is not None
                and other._text_length_max > self._text_length_max
            ):
                self._text_length_max = other._text_length_max

    @classmethod
    def from_json_dict(cls, payload: dict[str, object]) -> "StatsTracker":
        tracker = cls()
        tracker._record_counts = {
            key: int(value)
            for key, value in dict(payload["records"]).items()
        }
        tracker._failure_types = Counter(
            {
                key: int(value)
                for key, value in dict(payload["failure_types"]).items()
            }
        )
        tracker._shard_counts = {
            key: int(value)
            for key, value in dict(payload["shard_counts"]).items()
        }
        text_length = dict(payload["text_length"])
        tracker._text_length_count = int(text_length["count"])
        tracker._text_length_min = (
            int(text_length["min"]) if text_length["min"] is not None else None
        )
        tracker._text_length_max = (
            int(text_length["max"]) if text_length["max"] is not None else None
        )
        tracker._text_length_sum = int(text_length["sum"])
        return tracker

    def to_json_dict(self) -> dict[str, object]:
        mean = (
            self._text_length_sum / self._text_length_count
            if self._text_length_count
            else None
        )
        return {
            "records": dict(self._record_counts),
            "failure_types": dict(self._failure_types),
            "shard_counts": dict(self._shard_counts),
            "text_length": {
                "count": self._text_length_count,
                "min": self._text_length_min,
                "max": self._text_length_max,
                "sum": self._text_length_sum,
                "mean": mean,
            },
        }


def build_stats_tracker() -> StatsTracker:
    return StatsTracker()


class FailureLogger:
    def __init__(self, run_root: str | Path, run_id: str) -> None:
        self._run_root = Path(run_root)
        self._run_id = run_id
        self._path = parse_failures_log_path(self._run_root)

    def write_failure(
        self,
        *,
        split_id: str,
        stage: str,
        error_type: str,
        error_message: str,
        timestamp: str,
        page_id: int | None = None,
        title: str | None = None,
    ) -> None:
        event = FailureEvent(
            run_id=self._run_id,
            split_id=split_id,
            page_id=page_id,
            title=title,
            stage=stage,
            error_type=error_type,
            error_message=error_message,
            timestamp=timestamp,
        )
        self._append_json_line(
            {
                "timestamp": event.timestamp,
                "run_id": event.run_id,
                "split_id": event.split_id,
                "page_id": event.page_id,
                "title": event.title,
                "stage": event.stage,
                "error_type": event.error_type,
                "error_message": event.error_message,
            }
        )

    def _append_json_line(self, payload: dict[str, object]) -> None:
        _ensure_parent(self._path)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")


def build_failure_logger(run_root: str | Path, run_id: str) -> FailureLogger:
    return FailureLogger(run_root, run_id)


class RunEventLogger:
    def __init__(self, run_root: str | Path, run_id: str) -> None:
        self._run_root = Path(run_root)
        self._run_id = run_id
        self._path = run_events_log_path(self._run_root)

    def write_event(
        self,
        *,
        event_type: str,
        timestamp: str,
        split_id: str | None = None,
        message: str | None = None,
    ) -> None:
        payload = {
            "timestamp": timestamp,
            "run_id": self._run_id,
            "event_type": event_type,
            "split_id": split_id,
            "message": message,
        }
        _ensure_parent(self._path)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")


def build_run_event_logger(run_root: str | Path, run_id: str) -> RunEventLogger:
    return RunEventLogger(run_root, run_id)


def write_run_manifest(run_root: str | Path, audit_context: RunAuditContext) -> Path:
    return _write_atomic_json(
        Path(run_root),
        run_manifest_path(".").relative_to("."),
        audit_context.to_json_dict(),
    )


def write_split_manifest(run_root: str | Path, manifest: SplitManifest) -> Path:
    return _write_atomic_json(
        Path(run_root),
        split_manifest_path(".", manifest.split_id).relative_to("."),
        manifest.to_json_dict(),
    )


def load_split_manifest(run_root: str | Path, split_id: str) -> SplitManifest:
    payload = json.loads(split_manifest_path(run_root, split_id).read_text(encoding="utf-8"))
    return SplitManifest(
        split_id=payload["split_id"],
        input_file=payload["input_file"],
        status=SplitStatus(payload["status"]),
        articles_shards=payload["articles_shards"],
        redirect_aliases_shards=payload["redirect_aliases_shards"],
        disambiguation_shards=payload["disambiguation_shards"],
        pages_seen=payload["pages_seen"],
        pages_emitted=payload["pages_emitted"],
        failures=payload["failures"],
        started_at=payload["started_at"],
        finished_at=payload["finished_at"],
    )


def _load_split_manifest_if_exists(run_root: Path, split_id: str) -> SplitManifest | None:
    path = split_manifest_path(run_root, split_id)
    if not path.exists():
        return None
    return load_split_manifest(run_root, split_id)


def _merge_split_manifests(
    existing: SplitManifest | None,
    current: SplitManifest,
) -> SplitManifest:
    if existing is None:
        return current
    if existing.input_file != current.input_file:
        raise ValueError("input_file must remain stable for a given split manifest")
    return SplitManifest(
        split_id=current.split_id,
        input_file=current.input_file,
        status=current.status,
        articles_shards=existing.articles_shards + current.articles_shards,
        redirect_aliases_shards=(
            existing.redirect_aliases_shards + current.redirect_aliases_shards
        ),
        disambiguation_shards=(
            existing.disambiguation_shards + current.disambiguation_shards
        ),
        pages_seen=existing.pages_seen + current.pages_seen,
        pages_emitted=existing.pages_emitted + current.pages_emitted,
        failures=existing.failures + current.failures,
        started_at=existing.started_at or current.started_at,
        finished_at=current.finished_at or existing.finished_at,
    )


def _load_split_stats_if_exists(run_root: Path, split_id: str) -> StatsTracker | None:
    path = split_stats_path(run_root, split_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return StatsTracker.from_json_dict(payload)


def _artifact_shard_count(
    manifest: SplitManifest | None,
    artifact_kind: str,
) -> int:
    if manifest is None:
        return 0
    if artifact_kind == "articles":
        return manifest.articles_shards
    if artifact_kind == "redirect_aliases":
        return manifest.redirect_aliases_shards
    return manifest.disambiguation_shards


class DeterministicShardWriter:
    def __init__(
        self,
        *,
        run_root: str | Path,
        split_id: str,
        input_file: str | Path,
        artifact_kind: str,
        shard_max_records: int,
        shard_max_uncompressed_bytes: int,
    ) -> None:
        self._run_root = Path(run_root)
        self._split_id = split_id
        self._input_file = Path(input_file)
        self._artifact_kind = artifact_kind
        self._shard_max_records = shard_max_records
        self._shard_max_uncompressed_bytes = shard_max_uncompressed_bytes
        self._current_lines: list[bytes] = []
        self._current_records = 0
        self._current_uncompressed_bytes = 0
        self._shard_count = 0
        self._initial_shard_count = 0
        self._shard_state_synced = False
        self._promoted_shard_paths: list[Path] = []
        self._pages_seen = 0
        self._pages_emitted = 0
        self._stats = build_stats_tracker()
        self._closed = False

    def write(self, record: JsonRecord) -> None:
        if self._closed:
            raise RuntimeError("writer is already closed")
        encoded_line = (
            json.dumps(record.to_json_dict(), ensure_ascii=False).encode("utf-8") + b"\n"
        )
        if self._should_roll_shard(len(encoded_line)):
            try:
                self._flush_current_shard()
            except Exception:
                self._rollback_promoted_shards()
                raise
        self._current_lines.append(encoded_line)
        self._current_records += 1
        self._current_uncompressed_bytes += len(encoded_line)
        self._pages_seen += 1
        self._pages_emitted += 1
        self._record_stats(record)

    def close(self) -> None:
        if self._closed:
            return
        stats_path = split_stats_path(self._run_root, self._split_id)
        manifest_path = split_manifest_path(self._run_root, self._split_id)
        previous_stats = (
            stats_path.read_bytes() if stats_path.exists() else None
        )
        previous_manifest = (
            manifest_path.read_bytes() if manifest_path.exists() else None
        )
        try:
            if self._current_lines:
                self._flush_current_shard()
            manifest = SplitManifest(
                split_id=self._split_id,
                input_file=self._input_file,
                status=SplitStatus.completed,
                articles_shards=(
                    self._shard_count - self._initial_shard_count
                    if self._artifact_kind == "articles"
                    else 0
                ),
                redirect_aliases_shards=(
                    self._shard_count - self._initial_shard_count
                    if self._artifact_kind == "redirect_aliases"
                    else 0
                ),
                disambiguation_shards=(
                    self._shard_count - self._initial_shard_count
                    if self._artifact_kind == "disambiguation"
                    else 0
                ),
                pages_seen=self._pages_seen,
                pages_emitted=self._pages_emitted,
                failures=0,
            )
            existing_manifest = _load_split_manifest_if_exists(
                self._run_root,
                self._split_id,
            )
            merged_manifest = _merge_split_manifests(
                existing_manifest,
                manifest,
            )
            merged_stats = _load_split_stats_if_exists(self._run_root, self._split_id)
            if merged_stats is None:
                merged_stats = build_stats_tracker()
            merged_stats.merge(self._stats)
            _write_atomic_json(
                self._run_root,
                split_stats_path(".", self._split_id).relative_to("."),
                merged_stats.to_json_dict(),
            )
            write_split_manifest(self._run_root, merged_manifest)
        except Exception:
            self._restore_shared_state(stats_path, previous_stats)
            self._restore_shared_state(manifest_path, previous_manifest)
            self._rollback_promoted_shards()
            raise
        self._closed = True

    def _should_roll_shard(self, next_line_length: int) -> bool:
        if not self._current_lines:
            return False
        if self._current_records + 1 > self._shard_max_records:
            return True
        return (
            self._current_uncompressed_bytes + next_line_length
            > self._shard_max_uncompressed_bytes
        )

    def _sync_shard_state(self) -> None:
        if self._shard_state_synced:
            return
        existing_manifest = _load_split_manifest_if_exists(
            self._run_root,
            self._split_id,
        )
        self._shard_count = _artifact_shard_count(
            existing_manifest,
            self._artifact_kind,
        )
        self._initial_shard_count = self._shard_count
        self._shard_state_synced = True

    def _flush_current_shard(self) -> None:
        self._sync_shard_state()
        relative_path = (
            Path(self._artifact_kind)
            / self._split_id
            / f"shard-{self._shard_count:05d}.jsonl.zst"
        )
        payload = b"".join(self._current_lines)
        compressed = zstd.ZstdCompressor().compress(payload)
        final_path = _write_atomic_bytes(self._run_root, relative_path, compressed)
        self._promoted_shard_paths.append(final_path)
        self._stats.record_shard(self._artifact_kind)
        self._shard_count += 1
        self._current_lines = []
        self._current_records = 0
        self._current_uncompressed_bytes = 0

    def _record_stats(self, record: JsonRecord) -> None:
        if isinstance(record, ArticleRecord):
            self._stats.record_article(record.text_length)
            return
        if isinstance(record, RedirectAliasRecord):
            self._stats.record_redirect_alias()
            return
        if isinstance(record, DisambiguationRecord):
            self._stats.record_disambiguation()

    def _rollback_promoted_shards(self) -> None:
        for path in reversed(self._promoted_shard_paths):
            if path.exists():
                path.unlink()
        self._promoted_shard_paths.clear()

    def _restore_shared_state(self, path: Path, previous_payload: bytes | None) -> None:
        if previous_payload is None:
            if path.exists():
                path.unlink()
            return
        try:
            _write_atomic_bytes(
                self._run_root,
                path.relative_to(self._run_root),
                previous_payload,
            )
        except Exception:
            pass


def build_article_writer(
    *,
    run_root: str | Path,
    split_id: str,
    input_file: str | Path,
    shard_max_records: int,
    shard_max_uncompressed_bytes: int,
) -> DeterministicShardWriter:
    return DeterministicShardWriter(
        run_root=run_root,
        split_id=split_id,
        input_file=input_file,
        artifact_kind="articles",
        shard_max_records=shard_max_records,
        shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
    )


def build_redirect_alias_writer(
    *,
    run_root: str | Path,
    split_id: str,
    input_file: str | Path,
    shard_max_records: int,
    shard_max_uncompressed_bytes: int,
) -> DeterministicShardWriter:
    return DeterministicShardWriter(
        run_root=run_root,
        split_id=split_id,
        input_file=input_file,
        artifact_kind="redirect_aliases",
        shard_max_records=shard_max_records,
        shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
    )


def build_disambiguation_writer(
    *,
    run_root: str | Path,
    split_id: str,
    input_file: str | Path,
    shard_max_records: int,
    shard_max_uncompressed_bytes: int,
) -> DeterministicShardWriter:
    return DeterministicShardWriter(
        run_root=run_root,
        split_id=split_id,
        input_file=input_file,
        artifact_kind="disambiguation",
        shard_max_records=shard_max_records,
        shard_max_uncompressed_bytes=shard_max_uncompressed_bytes,
    )
