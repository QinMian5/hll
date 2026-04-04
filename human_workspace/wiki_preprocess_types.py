"""
Abstract: Typed contracts for the Wikipedia offline preprocessing pipeline.
Out of scope: XML traversal, wikitext cleaning, artifact writing, and CLI orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from math import isfinite
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import quote


def _require_non_empty_text(value: str, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    return text


def _require_zulu_timestamp(value: str, field_name: str) -> str:
    text = _require_non_empty_text(value, field_name)
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must use the fixed UTC format YYYY-MM-DDTHH:MM:SSZ"
        ) from exc
    return text


def _require_wikipedia_page_url(value: str, field_name: str) -> str:
    text = _require_non_empty_text(value, field_name)
    if not text.startswith("https://en.wikipedia.org/wiki/"):
        raise ValueError(f"{field_name} must be an enwiki page URL")
    return text


def _expected_enwiki_page_url(title: str) -> str:
    normalized_title = title.replace(" ", "_")
    return f"https://en.wikipedia.org/wiki/{quote(normalized_title, safe='()')}"


def _require_matching_page_url(source_url: str, title: str, field_name: str) -> str:
    url = _require_wikipedia_page_url(source_url, field_name)
    expected_url = _expected_enwiki_page_url(title)
    if url != expected_url:
        raise ValueError(
            f"{field_name} must match the canonical enwiki URL derived from title"
        )
    return url


def _require_positive_int(value: int, field_name: str) -> int:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value


def _require_non_negative_int(value: int, field_name: str) -> int:
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


def _require_ratio(value: float, field_name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")
    return value


def _require_path(value: str | Path, field_name: str) -> Path:
    if isinstance(value, Path):
        return value
    text = _require_non_empty_text(value, field_name)
    return Path(text)


def _freeze_json_like(value: Any, field_name: str) -> Any:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{field_name} must not contain non-finite float values")
        return value
    if isinstance(value, Mapping):
        frozen_mapping: dict[str, Any] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} must use string keys")
            frozen_mapping[key] = _freeze_json_like(
                nested_value,
                f"{field_name}.{key}",
            )
        return MappingProxyType(
            frozen_mapping
        )
    if isinstance(value, tuple | list):
        return tuple(
            _freeze_json_like(item, f"{field_name}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(f"{field_name} must contain only JSON-serializable values")


def _thaw_json_like(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_like(nested_value) for key, nested_value in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_like(item) for item in value]
    return value


class SplitStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed_threshold = "failed-threshold"


class PageKind(str, Enum):
    canonical_article = "canonical_article"
    redirect_alias = "redirect_alias"
    disambiguation = "disambiguation"
    ignored = "ignored"


@dataclass(frozen=True, slots=True)
class ArticleRecord:
    page_id: int
    title: str
    revision_id: int
    revision_timestamp: str
    source_dump: str
    source_url: str
    clean_text: str
    text_length: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _require_non_empty_text(self.title, "title"))
        object.__setattr__(
            self,
            "revision_timestamp",
            _require_zulu_timestamp(self.revision_timestamp, "revision_timestamp"),
        )
        object.__setattr__(self, "source_dump", _require_non_empty_text(self.source_dump, "source_dump"))
        object.__setattr__(self, "source_url", _require_matching_page_url(self.source_url, self.title, "source_url"))
        object.__setattr__(self, "clean_text", self.clean_text.strip())
        object.__setattr__(self, "page_id", _require_positive_int(self.page_id, "page_id"))
        object.__setattr__(self, "revision_id", _require_positive_int(self.revision_id, "revision_id"))
        object.__setattr__(self, "text_length", _require_non_negative_int(self.text_length, "text_length"))
        if self.text_length != len(self.clean_text):
            raise ValueError("text_length must match the length of clean_text")

    def to_json_dict(self) -> dict[str, object]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "revision_id": self.revision_id,
            "revision_timestamp": self.revision_timestamp,
            "source_dump": self.source_dump,
            "source_url": self.source_url,
            "clean_text": self.clean_text,
            "text_length": self.text_length,
        }


@dataclass(frozen=True, slots=True)
class RedirectAliasRecord:
    redirect_title: str
    canonical_title: str
    source_dump: str
    source_url: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "redirect_title", _require_non_empty_text(self.redirect_title, "redirect_title"))
        object.__setattr__(self, "canonical_title", _require_non_empty_text(self.canonical_title, "canonical_title"))
        object.__setattr__(self, "source_dump", _require_non_empty_text(self.source_dump, "source_dump"))
        object.__setattr__(
            self,
            "source_url",
            _require_matching_page_url(self.source_url, self.redirect_title, "source_url"),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "redirect_title": self.redirect_title,
            "canonical_title": self.canonical_title,
            "source_dump": self.source_dump,
            "source_url": self.source_url,
        }


@dataclass(frozen=True, slots=True)
class DisambiguationRecord:
    page_id: int
    title: str
    source_url: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _require_non_empty_text(self.title, "title"))
        object.__setattr__(self, "source_url", _require_matching_page_url(self.source_url, self.title, "source_url"))
        object.__setattr__(self, "page_id", _require_positive_int(self.page_id, "page_id"))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "source_url": self.source_url,
        }


@dataclass(frozen=True, slots=True)
class RunConfig:
    input_root: Path
    output_root: Path
    source_dump: str
    shard_max_records: int
    shard_max_uncompressed_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_root", _require_path(self.input_root, "input_root"))
        object.__setattr__(self, "output_root", _require_path(self.output_root, "output_root"))
        object.__setattr__(self, "source_dump", _require_non_empty_text(self.source_dump, "source_dump"))
        object.__setattr__(self, "shard_max_records", _require_positive_int(self.shard_max_records, "shard_max_records"))
        object.__setattr__(
            self,
            "shard_max_uncompressed_bytes",
            _require_positive_int(self.shard_max_uncompressed_bytes, "shard_max_uncompressed_bytes"),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "input_root": str(self.input_root),
            "output_root": str(self.output_root),
            "source_dump": self.source_dump,
            "shard_max_records": self.shard_max_records,
            "shard_max_uncompressed_bytes": self.shard_max_uncompressed_bytes,
        }


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    max_global_failure_ratio: float
    max_global_failure_count: int
    max_consecutive_failures: int
    max_split_failure_ratio: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_global_failure_ratio",
            _require_ratio(self.max_global_failure_ratio, "max_global_failure_ratio"),
        )
        object.__setattr__(
            self,
            "max_global_failure_count",
            _require_non_negative_int(self.max_global_failure_count, "max_global_failure_count"),
        )
        object.__setattr__(
            self,
            "max_consecutive_failures",
            _require_positive_int(self.max_consecutive_failures, "max_consecutive_failures"),
        )
        object.__setattr__(
            self,
            "max_split_failure_ratio",
            _require_ratio(self.max_split_failure_ratio, "max_split_failure_ratio"),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "max_global_failure_ratio": self.max_global_failure_ratio,
            "max_global_failure_count": self.max_global_failure_count,
            "max_consecutive_failures": self.max_consecutive_failures,
            "max_split_failure_ratio": self.max_split_failure_ratio,
        }


@dataclass(frozen=True, slots=True)
class RunAuditContext:
    run_id: str
    source_dump: str
    input_root: Path
    output_root: Path
    script_version: str
    cleaning_config: Mapping[str, Any] = field(default_factory=dict)
    split_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _require_non_empty_text(self.run_id, "run_id"))
        object.__setattr__(self, "source_dump", _require_non_empty_text(self.source_dump, "source_dump"))
        object.__setattr__(self, "input_root", _require_path(self.input_root, "input_root"))
        object.__setattr__(self, "output_root", _require_path(self.output_root, "output_root"))
        object.__setattr__(self, "script_version", _require_non_empty_text(self.script_version, "script_version"))
        object.__setattr__(self, "split_count", _require_non_negative_int(self.split_count, "split_count"))
        object.__setattr__(
            self,
            "cleaning_config",
            _freeze_json_like(self.cleaning_config, "cleaning_config"),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "source_dump": self.source_dump,
            "input_root": str(self.input_root),
            "output_root": str(self.output_root),
            "script_version": self.script_version,
            "cleaning_config": _thaw_json_like(self.cleaning_config),
            "split_count": self.split_count,
        }


@dataclass(frozen=True, slots=True)
class SplitManifest:
    split_id: str
    input_file: Path
    status: SplitStatus
    articles_shards: int = 0
    redirect_aliases_shards: int = 0
    disambiguation_shards: int = 0
    pages_seen: int = 0
    pages_emitted: int = 0
    failures: int = 0
    started_at: str | None = None
    finished_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "split_id", _require_non_empty_text(self.split_id, "split_id"))
        object.__setattr__(self, "input_file", _require_path(self.input_file, "input_file"))
        object.__setattr__(self, "articles_shards", _require_non_negative_int(self.articles_shards, "articles_shards"))
        object.__setattr__(
            self,
            "redirect_aliases_shards",
            _require_non_negative_int(self.redirect_aliases_shards, "redirect_aliases_shards"),
        )
        object.__setattr__(
            self,
            "disambiguation_shards",
            _require_non_negative_int(self.disambiguation_shards, "disambiguation_shards"),
        )
        object.__setattr__(self, "pages_seen", _require_non_negative_int(self.pages_seen, "pages_seen"))
        object.__setattr__(self, "pages_emitted", _require_non_negative_int(self.pages_emitted, "pages_emitted"))
        object.__setattr__(self, "failures", _require_non_negative_int(self.failures, "failures"))
        if self.started_at is not None:
            object.__setattr__(self, "started_at", _require_zulu_timestamp(self.started_at, "started_at"))
        if self.finished_at is not None:
            object.__setattr__(
                self,
                "finished_at",
                _require_zulu_timestamp(self.finished_at, "finished_at"),
            )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "split_id": self.split_id,
            "input_file": str(self.input_file),
            "status": self.status.value,
            "articles_shards": self.articles_shards,
            "redirect_aliases_shards": self.redirect_aliases_shards,
            "disambiguation_shards": self.disambiguation_shards,
            "pages_seen": self.pages_seen,
            "pages_emitted": self.pages_emitted,
            "failures": self.failures,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass(frozen=True, slots=True)
class PageExtractionResult:
    page_id: int
    title: str
    ns: int
    revision_id: int
    revision_timestamp: str
    source_dump: str
    source_url: str
    raw_text: str
    kind: PageKind = PageKind.canonical_article
    redirect_target: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "page_id", _require_positive_int(self.page_id, "page_id"))
        object.__setattr__(self, "title", _require_non_empty_text(self.title, "title"))
        object.__setattr__(self, "ns", self.ns)
        object.__setattr__(self, "revision_id", _require_positive_int(self.revision_id, "revision_id"))
        object.__setattr__(
            self,
            "revision_timestamp",
            _require_zulu_timestamp(self.revision_timestamp, "revision_timestamp"),
        )
        object.__setattr__(self, "source_dump", _require_non_empty_text(self.source_dump, "source_dump"))
        object.__setattr__(self, "source_url", _require_matching_page_url(self.source_url, self.title, "source_url"))
        object.__setattr__(self, "raw_text", self.raw_text)
        if self.redirect_target is not None:
            object.__setattr__(self, "redirect_target", _require_non_empty_text(self.redirect_target, "redirect_target"))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "ns": self.ns,
            "revision_id": self.revision_id,
            "revision_timestamp": self.revision_timestamp,
            "source_dump": self.source_dump,
            "source_url": self.source_url,
            "raw_text": self.raw_text,
            "kind": self.kind.value,
            "redirect_target": self.redirect_target,
        }


@dataclass(frozen=True, slots=True)
class FailureEvent:
    run_id: str
    split_id: str
    stage: str
    error_type: str
    error_message: str
    timestamp: str
    page_id: int | None = None
    title: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _require_non_empty_text(self.run_id, "run_id"))
        object.__setattr__(self, "split_id", _require_non_empty_text(self.split_id, "split_id"))
        object.__setattr__(self, "stage", _require_non_empty_text(self.stage, "stage"))
        object.__setattr__(self, "error_type", _require_non_empty_text(self.error_type, "error_type"))
        object.__setattr__(self, "error_message", _require_non_empty_text(self.error_message, "error_message"))
        object.__setattr__(self, "timestamp", _require_zulu_timestamp(self.timestamp, "timestamp"))
        if self.page_id is not None:
            object.__setattr__(self, "page_id", _require_positive_int(self.page_id, "page_id"))
        if self.title is not None:
            object.__setattr__(self, "title", _require_non_empty_text(self.title, "title"))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "split_id": self.split_id,
            "page_id": self.page_id,
            "title": self.title,
            "stage": self.stage,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }
