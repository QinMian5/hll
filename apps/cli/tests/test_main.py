from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

CLI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CLI_ROOT))

import main  # noqa: E402


def _success_payload() -> str:
    return (
        '{"title_validity":{"passed":true,"reason":null},'
        '"title_content_alignment":{"passed":true,"reason":null},'
        '"title_style_validity":{"passed":true,"reason":null},'
        '"content_coherence":{"passed":true,"reason":null},'
        '"content_atomicity":{"passed":true,"reason":null},'
        '"content_latex_validity":{"passed":true,"reason":null}}'
    )


def test_run_cursor_review_retries_until_output_matches_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"type":"result","result":"not-json"}',
            stderr="",
        ),
        subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"type":"result","result":"{\\"unexpected\\": true}"}',
            stderr="",
        ),
        subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"type": "result", "result": _success_payload()}),
            stderr="",
        ),
    ]
    calls: list[list[str]] = []

    def fake_run(
        args: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: float,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return responses[len(calls) - 1]

    monkeypatch.setattr(main.subprocess, "run", fake_run)

    settings = main.CliSettings(
        review_backend="cursor-agent",
        cursor_agent_workspace="/tmp/cursor-agent-review-probe",
        cursor_agent_max_retries=3,
    )

    review = main.run_cursor_review(
        title="Quadratic Discriminant Definition",
        content="The discriminant is defined as \\(b^2 - 4ac\\).",
        settings=settings,
    )

    assert review.passed() is True
    assert len(calls) == 3
    assert "--sandbox" in calls[0]
    assert "enabled" in calls[0]
    assert "--trust" in calls[0]


def test_run_cursor_review_raises_after_three_invalid_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        args: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: float,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"type":"result","result":"not-json"}',
            stderr="",
        )

    monkeypatch.setattr(main.subprocess, "run", fake_run)

    settings = main.CliSettings(
        review_backend="cursor-agent",
        cursor_agent_workspace="/tmp/cursor-agent-review-probe",
        cursor_agent_max_retries=3,
    )

    with pytest.raises(
        RuntimeError, match="cursor-agent review failed after 3 attempts"
    ):
        main.run_cursor_review(
            title="Quadratic Discriminant Definition",
            content="The discriminant is defined as \\(b^2 - 4ac\\).",
            settings=settings,
        )


def test_submit_reviewed_card_returns_review_result_when_review_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = main.ReviewResult(
        title_validity=main.ReviewItem(passed=True, reason=None),
        title_content_alignment=main.ReviewItem(passed=True, reason=None),
        title_style_validity=main.ReviewItem(passed=True, reason=None),
        content_coherence=main.ReviewItem(passed=True, reason=None),
        content_atomicity=main.ReviewItem(passed=True, reason=None),
        content_latex_validity=main.ReviewItem(passed=True, reason=None),
    )

    monkeypatch.setattr(main, "run_review_graph", lambda payload, settings: expected)

    review = main.submit_reviewed_card(
        title="Quadratic Equation Standard Form",
        content="A quadratic equation has the form \\(ax^2 + bx + c = 0\\).",
    )

    assert review == expected


def test_cli_projects_shared_function_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_review = main.ReviewResult(
        title_validity=main.ReviewItem(passed=False, reason="too broad"),
        title_content_alignment=main.ReviewItem(passed=True, reason=None),
        title_style_validity=main.ReviewItem(passed=True, reason=None),
        content_coherence=main.ReviewItem(passed=True, reason=None),
        content_atomicity=main.ReviewItem(passed=True, reason=None),
        content_latex_validity=main.ReviewItem(passed=True, reason=None),
    )
    monkeypatch.setattr(
        main,
        "submit_reviewed_card",
        lambda title, content: failed_review,
    )

    runner = CliRunner()
    result = runner.invoke(
        main.cli,
        [
            "--title",
            "Math",
            "--content",
            "A quadratic equation has the form \\(ax^2 + bx + c = 0\\).",
        ],
    )

    assert result.exit_code == 1
    assert json.loads(result.output)["result"] == "failed"
