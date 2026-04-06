"""
Abstract: Unit tests for operator CLI argument mapping of taxonomy classification batch script.
Out of scope: Real runtime dependency assembly and cursor-agent invocation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from click.testing import CliRunner

from modules.taxonomy_classification.dto import (
    TaxonomyClassificationBatchResult,
)

_SCRIPT_PATH = Path(__file__).resolve().parents[5] / "scripts" / "taxonomy-classify-unassigned.py"


def _load_script_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "taxonomy_classify_unassigned_script",
        _SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _empty_result() -> TaxonomyClassificationBatchResult:
    return TaxonomyClassificationBatchResult(
        selected_count=0,
        assigned_count=0,
        unchanged_count=0,
        error_count=0,
        selected_node_ids=[],
        outcomes=[],
    )


@pytest.mark.unit
def test_cli_forwards_limit_and_max_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, int | None | bool] = {}

    async def _fake_runner(
        *,
        limit: int | None,
        max_workers: int | None,
        on_selection_resolved: object | None,
        on_node_finished: object | None,
    ) -> TaxonomyClassificationBatchResult:
        captured["limit"] = limit
        captured["max_workers"] = max_workers
        captured["has_on_selection_resolved"] = callable(on_selection_resolved)
        captured["has_on_node_finished"] = callable(on_node_finished)
        return _empty_result()

    monkeypatch.setattr(module, "run_taxonomy_classification", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--limit", "3", "--max-workers", "16"])

    assert result.exit_code == 0
    assert captured == {
        "limit": 3,
        "max_workers": 16,
        "has_on_selection_resolved": True,
        "has_on_node_finished": True,
    }


@pytest.mark.unit
def test_cli_defaults_to_all_when_limit_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, int | None | bool] = {}

    async def _fake_runner(
        *,
        limit: int | None,
        max_workers: int | None,
        on_selection_resolved: object | None,
        on_node_finished: object | None,
    ) -> TaxonomyClassificationBatchResult:
        captured["limit"] = limit
        captured["max_workers"] = max_workers
        captured["has_on_selection_resolved"] = callable(on_selection_resolved)
        captured["has_on_node_finished"] = callable(on_node_finished)
        return _empty_result()

    monkeypatch.setattr(module, "run_taxonomy_classification", _fake_runner)

    result = CliRunner().invoke(module.cli, [])

    assert result.exit_code == 0
    assert captured == {
        "limit": None,
        "max_workers": None,
        "has_on_selection_resolved": True,
        "has_on_node_finished": True,
    }
