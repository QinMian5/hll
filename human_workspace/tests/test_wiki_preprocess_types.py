"""
Abstract: Contract tests for the Wikipedia offline preprocessing types module.
Out of scope: XML parsing, cleaning logic, and artifact writing.
"""

import pytest

from wiki_preprocess_types import (
    ArticleRecord,
    DisambiguationRecord,
    FailureEvent,
    PageExtractionResult,
    PageKind,
    RedirectAliasRecord,
    RunConfig,
    RunAuditContext,
    SplitManifest,
    SplitStatus,
)


def test_article_record_enforces_exact_fields() -> None:
    record = ArticleRecord(
        page_id=1,
        title="Alan Turing",
        revision_id=10,
        revision_timestamp="2026-03-01T00:00:00Z",
        source_dump="enwiki-20260301",
        source_url="https://en.wikipedia.org/wiki/Alan_Turing",
        clean_text="Intro",
        text_length=5,
    )
    assert record.to_json_dict()["title"] == "Alan Turing"
    assert list(record.to_json_dict()) == [
        "page_id",
        "title",
        "revision_id",
        "revision_timestamp",
        "source_dump",
        "source_url",
        "clean_text",
        "text_length",
    ]


def test_redirect_source_url_uses_redirect_title() -> None:
    record = RedirectAliasRecord(
        redirect_title="USA",
        canonical_title="United States",
        source_dump="enwiki-20260301",
        source_url="https://en.wikipedia.org/wiki/USA",
    )
    assert record.source_url.endswith("/USA")


def test_disambiguation_record_enforces_exact_fields() -> None:
    record = DisambiguationRecord(
        page_id=7,
        title="Mercury (disambiguation)",
        source_url="https://en.wikipedia.org/wiki/Mercury_(disambiguation)",
    )
    assert record.to_json_dict() == {
        "page_id": 7,
        "title": "Mercury (disambiguation)",
        "source_url": "https://en.wikipedia.org/wiki/Mercury_(disambiguation)",
    }


def test_run_config_requires_positive_shard_limits() -> None:
    with pytest.raises(ValueError):
        RunConfig(
            input_root=".",
            output_root=".",
            source_dump="enwiki-20260301",
            shard_max_records=0,
            shard_max_uncompressed_bytes=1024,
        )


def test_split_status_values_are_fixed() -> None:
    assert {status.value for status in SplitStatus} == {
        "pending",
        "running",
        "completed",
        "failed-threshold",
    }


def test_timestamps_use_utc_z_suffix() -> None:
    record = ArticleRecord(
        page_id=99,
        title="Mercury",
        revision_id=5,
        revision_timestamp="2026-03-01T00:00:00Z",
        source_dump="enwiki-20260301",
        source_url="https://en.wikipedia.org/wiki/Mercury",
        clean_text="Body",
        text_length=4,
    )
    assert record.to_json_dict()["revision_timestamp"].endswith("Z")


def test_article_record_rejects_non_z_timestamp() -> None:
    with pytest.raises(ValueError, match="revision_timestamp"):
        ArticleRecord(
            page_id=100,
            title="Bad Timestamp",
            revision_id=6,
            revision_timestamp="2026-03-01T00:00:00+00:00",
            source_dump="enwiki-20260301",
            source_url="https://en.wikipedia.org/wiki/Bad_Timestamp",
            clean_text="Body",
            text_length=4,
        )


def test_redirect_record_rejects_dump_provenance_url() -> None:
    with pytest.raises(ValueError, match="source_url"):
        RedirectAliasRecord(
            redirect_title="USA",
            canonical_title="United States",
            source_dump="enwiki-20260301",
            source_url="https://dumps.wikimedia.org/enwiki.xml.bz2",
        )


def test_article_record_rejects_mismatched_source_url() -> None:
    with pytest.raises(ValueError, match="source_url"):
        ArticleRecord(
            page_id=101,
            title="Alan Turing",
            revision_id=7,
            revision_timestamp="2026-03-01T00:00:00Z",
            source_dump="enwiki-20260301",
            source_url="https://en.wikipedia.org/wiki/Mercury",
            clean_text="Body",
            text_length=4,
        )


def test_split_manifest_rejects_non_utc_metadata_timestamps() -> None:
    with pytest.raises(ValueError, match="started_at"):
        SplitManifest(
            split_id="split-00001",
            input_file="split.xml.bz2",
            status=SplitStatus.running,
            started_at="not-z",
        )


def test_failure_event_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        FailureEvent(
            run_id="run-1",
            split_id="split-00001",
            page_id=5,
            title="Broken",
            stage="cleaning",
            error_type="ValueError",
            error_message="bad text",
            timestamp="not-a-timestampZ",
        )


def test_page_extraction_result_rejects_mismatched_source_url() -> None:
    with pytest.raises(ValueError, match="source_url"):
        PageExtractionResult(
            page_id=12,
            title="USA",
            ns=0,
            revision_id=44,
            revision_timestamp="2026-03-01T00:00:00Z",
            source_dump="enwiki-20260301",
            source_url="https://en.wikipedia.org/wiki/United_States",
            raw_text="#REDIRECT [[United States]]",
            kind=PageKind.redirect_alias,
            redirect_target="United States",
        )


def test_article_record_rejects_text_length_mismatch() -> None:
    with pytest.raises(ValueError, match="text_length"):
        ArticleRecord(
            page_id=102,
            title="Length mismatch",
            revision_id=8,
            revision_timestamp="2026-03-01T00:00:00Z",
            source_dump="enwiki-20260301",
            source_url="https://en.wikipedia.org/wiki/Length_mismatch",
            clean_text="Body",
            text_length=999,
        )


def test_run_audit_context_freezes_cleaning_config() -> None:
    original = {"mode": "human-readable", "nested": {"lists": ["a", "b"]}}
    context = RunAuditContext(
        run_id="run-1",
        source_dump="enwiki-20260301",
        input_root=".",
        output_root="./out",
        script_version="2026.04.03",
        cleaning_config=original,
        split_count=1,
    )

    original["nested"]["lists"].append("c")

    with pytest.raises(TypeError):
        context.cleaning_config["mode"] = "changed"  # type: ignore[index]

    assert context.cleaning_config["nested"]["lists"] == ("a", "b")
    assert context.to_json_dict()["cleaning_config"] == {
        "mode": "human-readable",
        "nested": {"lists": ["a", "b"]},
    }


def test_run_audit_context_rejects_non_json_cleaning_config_values() -> None:
    with pytest.raises(ValueError, match="cleaning_config"):
        RunAuditContext(
            run_id="run-1",
            source_dump="enwiki-20260301",
            input_root=".",
            output_root="./out",
            script_version="2026.04.03",
            cleaning_config={"bad": {1, 2}},
            split_count=1,
        )


def test_run_audit_context_rejects_non_string_cleaning_config_keys() -> None:
    with pytest.raises(ValueError, match="cleaning_config"):
        RunAuditContext(
            run_id="run-1",
            source_dump="enwiki-20260301",
            input_root=".",
            output_root="./out",
            script_version="2026.04.03",
            cleaning_config={1: "bad-key"},
            split_count=1,
        )


def test_run_audit_context_rejects_non_finite_float_values() -> None:
    with pytest.raises(ValueError, match="cleaning_config"):
        RunAuditContext(
            run_id="run-1",
            source_dump="enwiki-20260301",
            input_root=".",
            output_root="./out",
            script_version="2026.04.03",
            cleaning_config={"ratio": float("inf")},
            split_count=1,
        )
