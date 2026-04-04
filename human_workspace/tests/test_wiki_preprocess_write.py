"""
Abstract: Contract tests for deterministic Wikipedia preprocessing artifact writing.
Out of scope: XML parsing, page classification, and wikitext cleaning.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import zstandard as zstd

from wiki_preprocess_types import (
    ArticleRecord,
    DisambiguationRecord,
    RedirectAliasRecord,
    RunAuditContext,
    SplitManifest,
    SplitStatus,
)
from wiki_preprocess_write import (
    articles_dir,
    build_article_writer,
    build_disambiguation_writer,
    build_failure_logger,
    build_redirect_alias_writer,
    build_run_event_logger,
    build_stats_tracker,
    disambiguation_dir,
    load_split_manifest,
    logs_dir,
    manifests_dir,
    redirect_aliases_dir,
    run_events_log_path,
    run_manifest_path,
    stats_dir,
    temp_dir,
    write_run_manifest,
    write_split_manifest,
)


def _article_record(page_id: int) -> ArticleRecord:
    title = f"Title {page_id}"
    clean_text = f"Body {page_id}"
    return ArticleRecord(
        page_id=page_id,
        title=title,
        revision_id=page_id,
        revision_timestamp="2026-03-01T00:00:00Z",
        source_dump="enwiki-20260301",
        source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        clean_text=clean_text,
        text_length=len(clean_text),
    )


def _redirect_record() -> RedirectAliasRecord:
    return RedirectAliasRecord(
        redirect_title="USA",
        canonical_title="United States",
        source_dump="enwiki-20260301",
        source_url="https://en.wikipedia.org/wiki/USA",
    )


def _disambiguation_record() -> DisambiguationRecord:
    return DisambiguationRecord(
        page_id=7,
        title="Mercury (disambiguation)",
        source_url="https://en.wikipedia.org/wiki/Mercury_(disambiguation)",
    )


def _read_jsonl_zst(path: Path) -> list[dict[str, object]]:
    data = zstd.ZstdDecompressor().decompress(path.read_bytes()).decode("utf-8")
    return [json.loads(line) for line in data.splitlines() if line]


def test_run_root_path_helpers_cover_expected_subdirectories(tmp_path: Path) -> None:
    assert articles_dir(tmp_path) == tmp_path / "articles"
    assert redirect_aliases_dir(tmp_path) == tmp_path / "redirect_aliases"
    assert disambiguation_dir(tmp_path) == tmp_path / "disambiguation"
    assert manifests_dir(tmp_path) == tmp_path / "manifests"
    assert stats_dir(tmp_path) == tmp_path / "stats"
    assert logs_dir(tmp_path) == tmp_path / "logs"
    assert temp_dir(tmp_path) == tmp_path / "temp"


def test_article_writer_rolls_shards_after_record_threshold(tmp_path: Path) -> None:
    writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=2,
        shard_max_uncompressed_bytes=10_000,
    )
    writer.write(_article_record(1))
    writer.write(_article_record(2))
    writer.write(_article_record(3))
    writer.close()

    shard_dir = articles_dir(tmp_path) / "split-00001"
    assert sorted(shard_dir.glob("*.jsonl.zst")) == [
        shard_dir / "shard-00000.jsonl.zst",
        shard_dir / "shard-00001.jsonl.zst",
    ]
    assert _read_jsonl_zst(shard_dir / "shard-00000.jsonl.zst") == [
        _article_record(1).to_json_dict(),
        _article_record(2).to_json_dict(),
    ]
    assert _read_jsonl_zst(shard_dir / "shard-00001.jsonl.zst") == [
        _article_record(3).to_json_dict(),
    ]


@pytest.mark.parametrize(
    ("builder", "record", "expected_dir", "expected_dict"),
    [
        (
            build_redirect_alias_writer,
            _redirect_record(),
            redirect_aliases_dir,
            {
                "redirect_title": "USA",
                "canonical_title": "United States",
                "source_dump": "enwiki-20260301",
                "source_url": "https://en.wikipedia.org/wiki/USA",
            },
        ),
        (
            build_disambiguation_writer,
            _disambiguation_record(),
            disambiguation_dir,
            {
                "page_id": 7,
                "title": "Mercury (disambiguation)",
                "source_url": "https://en.wikipedia.org/wiki/Mercury_(disambiguation)",
            },
        ),
    ],
)
def test_non_article_writers_emit_expected_jsonl_zst(
    builder,
    record,
    expected_dir,
    expected_dict,
    tmp_path: Path,
) -> None:
    writer = builder(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )
    writer.write(record)
    writer.close()

    shard_dir = expected_dir(tmp_path) / "split-00001"
    assert _read_jsonl_zst(shard_dir / "shard-00000.jsonl.zst") == [expected_dict]


def test_split_manifest_round_trip_is_manifest_driven_not_output_guessing(tmp_path: Path) -> None:
    manifest = SplitManifest(
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        status=SplitStatus.completed,
        articles_shards=2,
        redirect_aliases_shards=1,
        disambiguation_shards=1,
        pages_seen=4,
        pages_emitted=3,
        failures=0,
        started_at="2026-03-01T00:00:00Z",
        finished_at="2026-03-01T00:10:00Z",
    )

    write_split_manifest(tmp_path, manifest)

    assert load_split_manifest(tmp_path, "split-00001") == manifest


def test_load_split_manifest_does_not_infer_state_from_output_files(tmp_path: Path) -> None:
    shard_dir = articles_dir(tmp_path) / "split-00001"
    shard_dir.mkdir(parents=True, exist_ok=True)
    (shard_dir / "shard-00000.jsonl.zst").write_bytes(b"not-a-manifest")

    with pytest.raises(FileNotFoundError):
        load_split_manifest(tmp_path, "split-00001")


def test_run_manifest_persists_immutable_audit_context(tmp_path: Path) -> None:
    context = RunAuditContext(
        run_id="run-1",
        source_dump="enwiki-20260301",
        input_root="/data/enwiki",
        output_root=tmp_path,
        script_version="2026.04.03",
        cleaning_config={"mode": "human-readable", "nested": {"lists": ["a", "b"]}},
        split_count=1,
    )

    write_run_manifest(tmp_path, context)

    payload = json.loads(run_manifest_path(tmp_path).read_text())
    assert list(payload) == [
        "run_id",
        "source_dump",
        "input_root",
        "output_root",
        "script_version",
        "cleaning_config",
        "split_count",
    ]
    assert payload["run_id"] == "run-1"
    assert payload["cleaning_config"] == {"mode": "human-readable", "nested": {"lists": ["a", "b"]}}


def test_failure_logger_preserves_key_order(tmp_path: Path) -> None:
    logger = build_failure_logger(tmp_path, run_id="run-1")
    logger.write_failure(
        split_id="split-00001",
        page_id=12,
        title="Broken",
        stage="cleaning",
        error_type="ValueError",
        error_message="broken text",
        timestamp="2026-03-01T00:00:00Z",
    )

    payload = json.loads((logs_dir(tmp_path) / "parse_failures.jsonl").read_text())
    assert list(payload) == [
        "timestamp",
        "run_id",
        "split_id",
        "page_id",
        "title",
        "stage",
        "error_type",
        "error_message",
    ]


def test_run_event_logger_preserves_key_order(tmp_path: Path) -> None:
    logger = build_run_event_logger(tmp_path, run_id="run-1")
    logger.write_event(
        event_type="split-started",
        timestamp="2026-03-01T00:00:00Z",
        split_id="split-00001",
        message="started",
    )

    payload = json.loads(run_events_log_path(tmp_path).read_text())
    assert list(payload) == [
        "timestamp",
        "run_id",
        "event_type",
        "split_id",
        "message",
    ]


def test_stats_tracker_aggregates_counts_failure_types_shards_and_text_length() -> None:
    stats = build_stats_tracker()
    stats.record_article(text_length=4)
    stats.record_article(text_length=8)
    stats.record_redirect_alias()
    stats.record_disambiguation()
    stats.record_failure("ValueError")
    stats.record_shard("articles")
    stats.record_shard("articles")
    stats.record_shard("redirect_aliases")

    payload = stats.to_json_dict()
    assert payload["records"] == {
        "canonical_article": 2,
        "redirect_alias": 1,
        "disambiguation": 1,
        "ignored": 0,
    }
    assert payload["failure_types"] == {"ValueError": 1}
    assert payload["shard_counts"] == {
        "articles": 2,
        "redirect_aliases": 1,
        "disambiguation": 0,
    }
    assert payload["text_length"] == {
        "count": 2,
        "min": 4,
        "max": 8,
        "sum": 12,
        "mean": 6.0,
    }


def test_writer_close_does_not_finalize_manifest_or_stats_when_promotion_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )
    writer.write(_article_record(1))

    def _fail_replace(*args: object, **kwargs: object) -> None:
        raise OSError("promotion failed")

    monkeypatch.setattr("wiki_preprocess_write.os.replace", _fail_replace)

    with pytest.raises(OSError, match="promotion failed"):
        writer.close()

    assert not run_manifest_path(tmp_path).exists()
    assert not (stats_dir(tmp_path) / "split-00001.json").exists()
    assert not (manifests_dir(tmp_path) / "split-00001.json").exists()


def test_multiple_writers_merge_split_manifest_and_stats(tmp_path: Path) -> None:
    article_writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )
    redirect_writer = build_redirect_alias_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )

    article_writer.write(_article_record(1))
    article_writer.close()
    redirect_writer.write(_redirect_record())
    redirect_writer.close()

    manifest = load_split_manifest(tmp_path, "split-00001")
    assert manifest.articles_shards == 1
    assert manifest.redirect_aliases_shards == 1
    assert manifest.disambiguation_shards == 0
    assert manifest.pages_seen == 2
    assert manifest.pages_emitted == 2

    payload = json.loads((stats_dir(tmp_path) / "split-00001.json").read_text())
    assert payload["records"]["canonical_article"] == 1
    assert payload["records"]["redirect_alias"] == 1
    assert payload["shard_counts"]["articles"] == 1
    assert payload["shard_counts"]["redirect_aliases"] == 1


def test_same_artifact_writer_reopen_uses_next_shard_index(tmp_path: Path) -> None:
    first_writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )
    second_writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )

    first_writer.write(_article_record(1))
    first_writer.close()
    second_writer.write(_article_record(2))
    second_writer.close()

    shard_dir = articles_dir(tmp_path) / "split-00001"
    assert sorted(shard_dir.glob("*.jsonl.zst")) == [
        shard_dir / "shard-00000.jsonl.zst",
        shard_dir / "shard-00001.jsonl.zst",
    ]
    assert _read_jsonl_zst(shard_dir / "shard-00000.jsonl.zst") == [
        _article_record(1).to_json_dict(),
    ]
    assert _read_jsonl_zst(shard_dir / "shard-00001.jsonl.zst") == [
        _article_record(2).to_json_dict(),
    ]

    manifest = load_split_manifest(tmp_path, "split-00001")
    assert manifest.articles_shards == 2
    assert manifest.pages_seen == 2
    assert manifest.pages_emitted == 2


def test_writer_close_does_not_publish_manifest_when_stats_finalize_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )
    writer.write(_article_record(1))

    real_replace = os.replace

    def _fail_stats_replace(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        if str(destination).endswith("/stats/split-00001.json"):
            raise OSError("stats finalize failed")
        real_replace(source, destination)

    monkeypatch.setattr("wiki_preprocess_write.os.replace", _fail_stats_replace)

    with pytest.raises(OSError, match="stats finalize failed"):
        writer.close()

    assert not (manifests_dir(tmp_path) / "split-00001.json").exists()
    assert not (stats_dir(tmp_path) / "split-00001.json").exists()
    assert not list((articles_dir(tmp_path) / "split-00001").glob("*.jsonl.zst"))


def test_writer_close_rolls_back_outputs_when_manifest_finalize_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )
    writer.write(_article_record(1))

    real_replace = os.replace

    def _fail_manifest_replace(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
    ) -> None:
        if str(destination).endswith("/manifests/split-00001.json"):
            raise OSError("manifest finalize failed")
        real_replace(source, destination)

    monkeypatch.setattr("wiki_preprocess_write.os.replace", _fail_manifest_replace)

    with pytest.raises(OSError, match="manifest finalize failed"):
        writer.close()

    assert not (manifests_dir(tmp_path) / "split-00001.json").exists()
    assert not (stats_dir(tmp_path) / "split-00001.json").exists()
    assert not list((articles_dir(tmp_path) / "split-00001").glob("*.jsonl.zst"))


def test_manifest_merge_rejects_conflicting_input_file_provenance(tmp_path: Path) -> None:
    first_writer = build_article_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-00000.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )
    second_writer = build_redirect_alias_writer(
        run_root=tmp_path,
        split_id="split-00001",
        input_file=tmp_path / "pages-articles-multistream-00001.xml-99999.bz2",
        shard_max_records=10,
        shard_max_uncompressed_bytes=10_000,
    )

    first_writer.write(_article_record(1))
    first_writer.close()
    second_writer.write(_redirect_record())

    with pytest.raises(ValueError, match="input_file"):
        second_writer.close()
