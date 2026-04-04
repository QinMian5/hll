"""
Abstract: End-to-end contract tests for the Wikipedia preprocessing controller pipeline.
Out of scope: Unit-level parsing internals, cleaner implementation details, and downloader behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import zstandard as zstd

from wiki_preprocess import (
    ThresholdAbort,
    discover_split_inputs,
    evaluate_thresholds,
    load_index_page_counts,
    run_pipeline,
)
from wiki_preprocess_types import SplitManifest, SplitStatus, ThresholdConfig
from wiki_preprocess_write import (
    load_run_stats,
    load_split_manifest,
    load_split_stats,
    write_split_manifest,
)


def _seed_running_manifest(run_root: Path, split_id: str) -> None:
    write_split_manifest(
        run_root,
        SplitManifest(
            split_id=split_id,
            input_file=run_root / "source.xml.bz2",
            status=SplitStatus.running,
            started_at="2026-03-01T00:00:00Z",
        ),
    )
    temp_dir = run_root / "temp" / split_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "stale.tmp").write_text("stale", encoding="utf-8")
    article_dir = run_root / "articles" / split_id
    article_dir.mkdir(parents=True, exist_ok=True)
    (article_dir / "shard-00000.jsonl.zst.partial").write_text(
        "partial",
        encoding="utf-8",
    )


def _read_threshold_abort(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _list_relative_outputs(run_root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(run_root))
        for path in run_root.rglob("*")
        if path.is_file()
    )


def _read_jsonl_zst(path: Path) -> list[str]:
    payload = zstd.ZstdDecompressor().decompress(path.read_bytes()).decode("utf-8")
    return [line for line in payload.splitlines() if line]


def _read_shard_payloads(run_root: Path) -> dict[str, list[str]]:
    return {
        str(path.relative_to(run_root)): _read_jsonl_zst(path)
        for path in sorted(run_root.rglob("*.jsonl.zst"))
    }


def test_discover_split_inputs_sorts_by_stable_file_name(sample_input_dir: Path) -> None:
    extra = sample_input_dir / "pages-articles-multistream-00002.xml-00000.bz2"
    extra.write_bytes(b"placeholder")
    ignored = sample_input_dir / "pages-articles-multistream.xml.bz2"
    ignored.write_bytes(b"not-a-split")
    (sample_input_dir / "foo-pages-articles-multistream-99999.xml-not-a-split.bz2").write_bytes(
        b"not-a-split",
    )
    (sample_input_dir / "pages-articles-multistream-backup.xml.bz2").write_bytes(
        b"not-a-split",
    )

    assert [path.name for path in discover_split_inputs(sample_input_dir)] == [
        "pages-articles-multistream-00001.xml-00000.bz2",
        "pages-articles-multistream-00002.xml-00000.bz2",
    ]


def test_pipeline_processes_split_into_all_artifact_classes(
    sample_input_dir: Path,
    tmp_path: Path,
) -> None:
    result = run_pipeline(
        input_root=sample_input_dir,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
    )

    assert result.completed_splits == ["split-00001"]
    assert (result.run_root / "articles" / "split-00001").exists()
    assert (result.run_root / "redirect_aliases" / "split-00001").exists()
    assert (result.run_root / "disambiguation" / "split-00001").exists()


def test_resume_restarts_interrupted_running_split_from_split_start(
    sample_input_dir: Path,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "runs" / "run-resume"
    _seed_running_manifest(run_root, split_id="split-00001")

    result = run_pipeline(
        input_root=sample_input_dir,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
        resume=True,
    )

    assert result.run_root == run_root
    assert load_split_manifest(result.run_root, "split-00001").status is SplitStatus.completed
    assert not (result.run_root / "temp" / "split-00001" / "stale.tmp").exists()
    assert not (
        result.run_root / "articles" / "split-00001" / "shard-00000.jsonl.zst.partial"
    ).exists()


def test_threshold_crossing_aborts_run_and_records_diagnostics(tmp_path: Path) -> None:
    with pytest.raises(ThresholdAbort):
        evaluate_thresholds(
            consecutive_failures=101,
            split_failure_ratio=0.50,
            global_failure_ratio=0.02,
            global_failure_count=5,
            recent_failures=[
                {
                    "page_id": 1,
                    "title": "Broken",
                    "stage": "cleaning",
                    "error_type": "ValueError",
                }
            ],
            affected_split_id="split-00001",
            logs_root=tmp_path / "logs",
            thresholds=ThresholdConfig(
                max_consecutive_failures=100,
                max_split_failure_ratio=0.25,
                max_global_failure_ratio=0.01,
                max_global_failure_count=10,
            ),
        )

    diagnostics = _read_threshold_abort(tmp_path / "logs" / "threshold_abort.json")
    assert diagnostics["trigger"] == "max_consecutive_failures"
    assert diagnostics["affected_split_id"] == "split-00001"
    assert diagnostics["error_type_distribution"] == {"ValueError": 1}


def test_pipeline_threshold_abort_marks_split_and_writes_diagnostics(
    sample_input_dir_with_one_broken_page: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(ThresholdAbort):
        run_pipeline(
            input_root=sample_input_dir_with_one_broken_page,
            output_root=tmp_path,
            source_dump="enwiki-20260301",
            thresholds=ThresholdConfig(
                max_consecutive_failures=100,
                max_split_failure_ratio=1.0,
                max_global_failure_ratio=1.0,
                max_global_failure_count=0,
            ),
        )

    run_root = tmp_path / "runs" / "run-00001"
    manifest = load_split_manifest(run_root, "split-00001")
    diagnostics = _read_threshold_abort(run_root / "logs" / "threshold_abort.json")

    assert manifest.status is SplitStatus.failed_threshold
    assert diagnostics["trigger"] == "max_global_failure_count"
    assert diagnostics["affected_split_id"] == "split-00001"


def test_global_failure_count_threshold_also_aborts(tmp_path: Path) -> None:
    with pytest.raises(ThresholdAbort):
        evaluate_thresholds(
            consecutive_failures=1,
            split_failure_ratio=0.10,
            global_failure_ratio=0.001,
            global_failure_count=11,
            recent_failures=[
                {
                    "page_id": 2,
                    "title": "Broken Count",
                    "stage": "xml_parse",
                    "error_type": "ParseError",
                }
            ],
            affected_split_id="split-00002",
            logs_root=tmp_path / "logs",
            thresholds=ThresholdConfig(
                max_consecutive_failures=100,
                max_split_failure_ratio=0.25,
                max_global_failure_ratio=0.01,
                max_global_failure_count=10,
            ),
        )


def test_non_canonical_pages_bypass_cleaning(sample_input_dir: Path, tmp_path: Path) -> None:
    cleaned_titles: list[str] = []

    def cleaner(page: object) -> str:
        cleaned_titles.append(page.title)
        return "cleaned"

    run_pipeline(
        input_root=sample_input_dir,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
        clean_page=cleaner,
    )

    assert cleaned_titles == ["Alan Turing"]


def test_unhandled_controller_exceptions_leave_split_marked_running(
    monkeypatch: pytest.MonkeyPatch,
    sample_input_dir: Path,
    tmp_path: Path,
) -> None:
    def _raise_runtime_error(page: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr("wiki_preprocess.classify_page", _raise_runtime_error)

    with pytest.raises(RuntimeError, match="boom"):
        run_pipeline(
            input_root=sample_input_dir,
            output_root=tmp_path,
            source_dump="enwiki-20260301",
        )

    manifest = load_split_manifest(tmp_path / "runs" / "run-00001", "split-00001")
    assert manifest.status is SplitStatus.running


def test_rerun_with_same_input_produces_same_shard_names_and_counts(
    sample_input_dir: Path,
    tmp_path: Path,
) -> None:
    first = run_pipeline(
        input_root=sample_input_dir,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
    )
    second = run_pipeline(
        input_root=sample_input_dir,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
    )

    first_manifest = load_split_manifest(first.run_root, "split-00001")
    second_manifest = load_split_manifest(second.run_root, "split-00001")

    assert _list_relative_outputs(first.run_root) == _list_relative_outputs(second.run_root)
    assert _read_shard_payloads(first.run_root) == _read_shard_payloads(second.run_root)
    assert load_run_stats(first.run_root) == load_run_stats(second.run_root)
    assert load_split_stats(first.run_root, "split-00001") == load_split_stats(
        second.run_root,
        "split-00001",
    )
    assert {
        "status": first_manifest.status,
        "articles_shards": first_manifest.articles_shards,
        "redirect_aliases_shards": first_manifest.redirect_aliases_shards,
        "disambiguation_shards": first_manifest.disambiguation_shards,
        "pages_seen": first_manifest.pages_seen,
        "pages_emitted": first_manifest.pages_emitted,
        "failures": first_manifest.failures,
    } == {
        "status": second_manifest.status,
        "articles_shards": second_manifest.articles_shards,
        "redirect_aliases_shards": second_manifest.redirect_aliases_shards,
        "disambiguation_shards": second_manifest.disambiguation_shards,
        "pages_seen": second_manifest.pages_seen,
        "pages_emitted": second_manifest.pages_emitted,
        "failures": second_manifest.failures,
    }


def test_single_page_failure_is_logged_but_run_continues(
    sample_input_dir_with_one_broken_page: Path,
    tmp_path: Path,
) -> None:
    result = run_pipeline(
        input_root=sample_input_dir_with_one_broken_page,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
    )

    manifest = load_split_manifest(result.run_root, "split-00001")
    failure_log = (result.run_root / "logs" / "parse_failures.jsonl").read_text(
        encoding="utf-8"
    )
    article_shards = _read_shard_payloads(result.run_root)
    assert result.status == "completed"
    assert manifest.pages_seen == 2
    assert manifest.failures == 1
    assert "Broken Page" in failure_log
    assert article_shards["articles/split-00001/shard-00000.jsonl.zst"] == [
        json.dumps(
            {
                "page_id": 100,
                "title": "Alan Turing",
                "revision_id": 1000,
                "revision_timestamp": "2026-03-01T00:00:00Z",
                "source_dump": "enwiki-20260301",
                "source_url": "https://en.wikipedia.org/wiki/Alan_Turing",
                "clean_text": "Lead sentence.",
                "text_length": 14,
            },
            ensure_ascii=False,
        ),
    ]


def test_index_pre_scan_counts_pages_for_each_unique_split_id(
    sample_input_dir_with_indexes_and_repeated_stream_number: Path,
) -> None:
    counts = load_index_page_counts(sample_input_dir_with_indexes_and_repeated_stream_number)

    assert counts == {
        "split-00015-p17324603p17460152": 3,
        "split-00015-p17460153p17560152": 3,
    }


def test_pipeline_uses_unique_split_ids_when_multistream_number_repeats(
    sample_input_dir_with_indexes_and_repeated_stream_number: Path,
    tmp_path: Path,
) -> None:
    result = run_pipeline(
        input_root=sample_input_dir_with_indexes_and_repeated_stream_number,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
    )

    assert result.completed_splits == [
        "split-00015-p17324603p17460152",
        "split-00015-p17460153p17560152",
    ]
    assert (
        result.run_root / "articles" / "split-00015-p17324603p17460152"
    ).exists()
    assert (
        result.run_root / "articles" / "split-00015-p17460153p17560152"
    ).exists()


def test_parallel_workers_preserve_outputs_for_multi_split_input(
    sample_input_dir_with_indexes_and_repeated_stream_number: Path,
    tmp_path: Path,
) -> None:
    serial = run_pipeline(
        input_root=sample_input_dir_with_indexes_and_repeated_stream_number,
        output_root=tmp_path / "serial",
        source_dump="enwiki-20260301",
        workers=1,
    )
    parallel = run_pipeline(
        input_root=sample_input_dir_with_indexes_and_repeated_stream_number,
        output_root=tmp_path / "parallel",
        source_dump="enwiki-20260301",
        workers=2,
    )

    assert _read_shard_payloads(serial.run_root) == _read_shard_payloads(parallel.run_root)
    assert load_run_stats(serial.run_root) == load_run_stats(parallel.run_root)
    for split_id in (
        "split-00015-p17324603p17460152",
        "split-00015-p17460153p17560152",
    ):
        serial_manifest = load_split_manifest(serial.run_root, split_id)
        parallel_manifest = load_split_manifest(parallel.run_root, split_id)
        assert {
            "status": serial_manifest.status,
            "articles_shards": serial_manifest.articles_shards,
            "redirect_aliases_shards": serial_manifest.redirect_aliases_shards,
            "disambiguation_shards": serial_manifest.disambiguation_shards,
            "pages_seen": serial_manifest.pages_seen,
            "pages_emitted": serial_manifest.pages_emitted,
            "failures": serial_manifest.failures,
        } == {
            "status": parallel_manifest.status,
            "articles_shards": parallel_manifest.articles_shards,
            "redirect_aliases_shards": parallel_manifest.redirect_aliases_shards,
            "disambiguation_shards": parallel_manifest.disambiguation_shards,
            "pages_seen": parallel_manifest.pages_seen,
            "pages_emitted": parallel_manifest.pages_emitted,
            "failures": parallel_manifest.failures,
        }


def test_progress_callback_receives_total_pages_and_final_processed_count(
    sample_input_dir_with_indexes_and_repeated_stream_number: Path,
    tmp_path: Path,
) -> None:
    snapshots: list[dict[str, object]] = []

    run_pipeline(
        input_root=sample_input_dir_with_indexes_and_repeated_stream_number,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
        workers=2,
        progress_callback=lambda snapshot: snapshots.append(dict(snapshot)),
    )

    assert snapshots[0]["total_pages"] == 6
    assert snapshots[0]["total_splits"] == 2
    assert any(int(snapshot["processed_pages"]) > 0 for snapshot in snapshots[1:])
    assert snapshots[-1]["processed_pages"] == 6
    assert snapshots[-1]["completed_splits"] == 2
    assert snapshots[-1]["status"] == "completed"


def test_parallel_resume_reuses_latest_run_and_skips_completed_splits(
    sample_input_dir_with_indexes_and_repeated_stream_number: Path,
    tmp_path: Path,
) -> None:
    first = run_pipeline(
        input_root=sample_input_dir_with_indexes_and_repeated_stream_number,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
        workers=2,
    )

    resumed = run_pipeline(
        input_root=sample_input_dir_with_indexes_and_repeated_stream_number,
        output_root=tmp_path,
        source_dump="enwiki-20260301",
        workers=2,
        resume=True,
    )

    assert resumed.run_root == first.run_root
    assert resumed.completed_splits == [
        "split-00015-p17324603p17460152",
        "split-00015-p17460153p17560152",
    ]


def test_parallel_global_failure_threshold_aborts_and_logs_failures(
    sample_input_dir_with_parallel_broken_pages: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(ThresholdAbort):
        run_pipeline(
            input_root=sample_input_dir_with_parallel_broken_pages,
            output_root=tmp_path,
            source_dump="enwiki-20260301",
            workers=2,
            thresholds=ThresholdConfig(
                max_consecutive_failures=100,
                max_split_failure_ratio=1.0,
                max_global_failure_ratio=1.0,
                max_global_failure_count=0,
            ),
        )

    run_root = tmp_path / "runs" / "run-00001"
    diagnostics = _read_threshold_abort(run_root / "logs" / "threshold_abort.json")
    failure_log = (run_root / "logs" / "parse_failures.jsonl").read_text(
        encoding="utf-8"
    )

    assert diagnostics["trigger"] == "max_global_failure_count"
    assert "Broken Alpha" in failure_log or "Broken Beta" in failure_log
