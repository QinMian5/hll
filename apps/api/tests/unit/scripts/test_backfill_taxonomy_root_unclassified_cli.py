"""
Abstract: Unit tests for root Unclassified backfill operator CLI mapping.
Out of scope: Database session behavior and projection rebuild correctness.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from entrypoints.ops import backfill_taxonomy_root_unclassified
from modules.taxonomy.root_unclassified_backfill import (
    TaxonomyRootUnclassifiedBackfillResult,
)


@pytest.mark.unit
def test_cli_defaults_to_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, bool] = {}

    async def _fake_runner(*, apply: bool) -> TaxonomyRootUnclassifiedBackfillResult:
        captured["apply"] = apply
        return TaxonomyRootUnclassifiedBackfillResult(
            mode="dry-run",
            root_id=None,
            root_unclassified_id=None,
            total_cards=3,
            assigned_before=0,
            missing_before=3,
            inserted_assignments=0,
            missing_after=3,
            projection_rebuilt=False,
        )

    monkeypatch.setattr(backfill_taxonomy_root_unclassified, "run_backfill", _fake_runner)

    result = CliRunner().invoke(backfill_taxonomy_root_unclassified.cli, [])

    assert result.exit_code == 0
    assert "mode=dry-run" in result.output
    assert "missing_before=3" in result.output
    assert captured == {"apply": False}


@pytest.mark.unit
def test_cli_requires_confirmation_for_apply() -> None:
    result = CliRunner().invoke(backfill_taxonomy_root_unclassified.cli, ["--apply"])

    assert result.exit_code != 0
    assert "--apply requires --confirm-backfill" in result.output


@pytest.mark.unit
def test_cli_forwards_confirmed_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, bool] = {}

    async def _fake_runner(*, apply: bool) -> TaxonomyRootUnclassifiedBackfillResult:
        captured["apply"] = apply
        return TaxonomyRootUnclassifiedBackfillResult(
            mode="apply",
            root_id=1,
            root_unclassified_id=2,
            total_cards=3,
            assigned_before=0,
            missing_before=3,
            inserted_assignments=3,
            missing_after=0,
            projection_rebuilt=True,
        )

    monkeypatch.setattr(backfill_taxonomy_root_unclassified, "run_backfill", _fake_runner)

    result = CliRunner().invoke(
        backfill_taxonomy_root_unclassified.cli,
        ["--apply", "--confirm-backfill"],
    )

    assert result.exit_code == 0
    assert "mode=apply" in result.output
    assert "inserted_assignments=3" in result.output
    assert captured == {"apply": True}
