"""
Abstract: Unit tests for taxonomy refinement job submission operator CLI mapping.
Out of scope: Live job-queue transport and database session behavior.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from click.testing import CliRunner

from modules.taxonomy_classification.dto import (
    TaxonomyClassificationScopeSummary,
    TaxonomyClassificationSubmissionResult,
    TaxonomyClassificationSubmissionSelection,
)

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[5] / "scripts" / "taxonomy-submit-refinement-jobs.py"
)


def _load_script_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "taxonomy_submit_refinement_jobs_script",
        _SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_cli_forwards_scope_name_and_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, TaxonomyClassificationSubmissionSelection | int | None] = {}

    async def _fake_runner(
        *,
        selection: TaxonomyClassificationSubmissionSelection,
        limit: int | None,
        batch_size: int,
        **_: object,
    ) -> TaxonomyClassificationSubmissionResult:
        captured["selection"] = selection
        captured["limit"] = limit
        captured["batch_size"] = batch_size
        return TaxonomyClassificationSubmissionResult(
            selected_scope_count=1,
            submitted_count=2,
            reused_idempotent_count=1,
            already_linked_count=1,
            skipped_no_children=0,
            scopes=[
                TaxonomyClassificationScopeSummary(
                    scope_node_id=4,
                    breadcrumb=("Root",),
                    regular_child_count=3,
                    submitted_count=2,
                    reused_idempotent_count=1,
                    already_linked_count=1,
                )
            ],
        )

    monkeypatch.setattr(module, "submit_refinement_jobs", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--scope-name", "root", "--limit", "10"])

    assert result.exit_code == 0
    assert "Selected scopes: 1" in result.output
    assert "Submitted: 2" in result.output
    assert "Reused idempotent: 1" in result.output
    assert "Already linked: 1" in result.output
    assert "Skipped no children: 0" in result.output
    assert "Scopes:" not in result.output
    selection = captured["selection"]
    assert isinstance(selection, TaxonomyClassificationSubmissionSelection)
    assert selection.kind == "scope_name"
    assert selection.scope_name == "root"
    assert captured["limit"] == 10
    assert captured["batch_size"] == 1000


@pytest.mark.unit
def test_cli_forwards_scope_path(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, TaxonomyClassificationSubmissionSelection | int | None] = {}

    async def _fake_runner(
        *,
        selection: TaxonomyClassificationSubmissionSelection,
        limit: int | None,
        batch_size: int,
        **_: object,
    ) -> TaxonomyClassificationSubmissionResult:
        captured["selection"] = selection
        captured["limit"] = limit
        captured["batch_size"] = batch_size
        return TaxonomyClassificationSubmissionResult(
            selected_scope_count=1,
            submitted_count=0,
            reused_idempotent_count=0,
            already_linked_count=0,
            skipped_no_children=0,
        )

    monkeypatch.setattr(module, "submit_refinement_jobs", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--scope-path", "Root / Science"])

    assert result.exit_code == 0
    selection = captured["selection"]
    assert isinstance(selection, TaxonomyClassificationSubmissionSelection)
    assert selection.kind == "scope_path"
    assert selection.scope_path == ("Root", "Science")
    assert captured["limit"] is None
    assert captured["batch_size"] == 1000


@pytest.mark.unit
def test_cli_forwards_all_unclassified(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, TaxonomyClassificationSubmissionSelection | int | None] = {}

    async def _fake_runner(
        *,
        selection: TaxonomyClassificationSubmissionSelection,
        limit: int | None,
        batch_size: int,
        **_: object,
    ) -> TaxonomyClassificationSubmissionResult:
        captured["selection"] = selection
        captured["limit"] = limit
        captured["batch_size"] = batch_size
        return TaxonomyClassificationSubmissionResult(
            selected_scope_count=2,
            submitted_count=0,
            reused_idempotent_count=0,
            already_linked_count=0,
            skipped_no_children=1,
            scopes=[
                TaxonomyClassificationScopeSummary(
                    scope_node_id=4,
                    breadcrumb=("Root", "Science"),
                    regular_child_count=0,
                    submitted_count=0,
                    reused_idempotent_count=0,
                    already_linked_count=0,
                    skipped_no_children=True,
                )
            ],
        )

    monkeypatch.setattr(module, "submit_refinement_jobs", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--all-unclassified"])

    assert result.exit_code == 0
    assert "Skipped no children: 1" in result.output
    assert "Root / Science" not in result.output
    selection = captured["selection"]
    assert isinstance(selection, TaxonomyClassificationSubmissionSelection)
    assert selection.kind == "all_unclassified"
    assert captured["limit"] is None
    assert captured["batch_size"] == 1000


@pytest.mark.unit
def test_cli_forwards_custom_batch_size(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, int] = {}

    async def _fake_runner(
        *,
        selection: TaxonomyClassificationSubmissionSelection,
        limit: int | None,
        batch_size: int,
        **_: object,
    ) -> TaxonomyClassificationSubmissionResult:
        assert selection.kind == "all_unclassified"
        assert limit is None
        captured["batch_size"] = batch_size
        return TaxonomyClassificationSubmissionResult(
            selected_scope_count=0,
            submitted_count=0,
            reused_idempotent_count=0,
            already_linked_count=0,
            skipped_no_children=0,
        )

    monkeypatch.setattr(module, "submit_refinement_jobs", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--all-unclassified", "--batch-size", "250"])

    assert result.exit_code == 0
    assert captured["batch_size"] == 250


@pytest.mark.unit
def test_cli_verbose_includes_scope_details(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()

    async def _fake_runner(
        *,
        selection: TaxonomyClassificationSubmissionSelection,
        limit: int | None,
        batch_size: int,
        **_: object,
    ) -> TaxonomyClassificationSubmissionResult:
        assert selection.kind == "all_unclassified"
        assert limit is None
        assert batch_size == 1000
        return TaxonomyClassificationSubmissionResult(
            selected_scope_count=1,
            submitted_count=1,
            reused_idempotent_count=0,
            already_linked_count=0,
            skipped_no_children=0,
            scopes=[
                TaxonomyClassificationScopeSummary(
                    scope_node_id=4,
                    breadcrumb=("Root", "Science"),
                    regular_child_count=2,
                    submitted_count=1,
                    reused_idempotent_count=0,
                    already_linked_count=0,
                    skipped_no_children=False,
                )
            ],
        )

    monkeypatch.setattr(module, "submit_refinement_jobs", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--all-unclassified", "--verbose"])

    assert result.exit_code == 0
    assert "Scopes:" in result.output
    assert "Root / Science" in result.output


@pytest.mark.unit
def test_cli_rejects_batch_size_above_job_queue_limit() -> None:
    module = _load_script_module()

    result = CliRunner().invoke(module.cli, ["--all-unclassified", "--batch-size", "1001"])

    assert result.exit_code != 0
    assert "Invalid value for '--batch-size'" in result.output


@pytest.mark.unit
def test_cli_rejects_multiple_scope_selectors() -> None:
    module = _load_script_module()

    result = CliRunner().invoke(
        module.cli,
        ["--scope-name", "Root", "--all-unclassified"],
    )

    assert result.exit_code != 0
    assert "Choose exactly one scope selector" in result.output
