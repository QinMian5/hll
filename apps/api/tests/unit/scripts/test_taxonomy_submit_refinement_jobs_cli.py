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
def test_cli_forwards_scope_node_id_and_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, int | None] = {}

    async def _fake_runner(*, scope_node_id: int, limit: int | None) -> int:
        captured["scope_node_id"] = scope_node_id
        captured["limit"] = limit
        return 2

    monkeypatch.setattr(module, "submit_refinement_jobs", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--scope-node-id", "4", "--limit", "10"])

    assert result.exit_code == 0
    assert "Submitted 2 taxonomy classification jobs." in result.output
    assert captured == {"scope_node_id": 4, "limit": 10}


@pytest.mark.unit
def test_cli_defaults_to_all_cards_when_limit_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script_module()
    captured: dict[str, int | None] = {}

    async def _fake_runner(*, scope_node_id: int, limit: int | None) -> int:
        captured["scope_node_id"] = scope_node_id
        captured["limit"] = limit
        return 0

    monkeypatch.setattr(module, "submit_refinement_jobs", _fake_runner)

    result = CliRunner().invoke(module.cli, ["--scope-node-id", "4"])

    assert result.exit_code == 0
    assert "Submitted 0 taxonomy classification jobs." in result.output
    assert captured == {"scope_node_id": 4, "limit": None}
