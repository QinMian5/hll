from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CLI_ROOT))

import main  # noqa: E402


def _success_payload() -> str:
    return (
        '{"title_validity":{"passed":true,"reason":null},'
        '"title_content_alignment":{"passed":true,"reason":null},'
        '"content_coherence":{"passed":true,"reason":null},'
        '"content_atomicity":{"passed":true,"reason":null},'
        '"content_latex_validity":{"passed":true,"reason":null}}'
    )


def test_build_cursor_review_prompt_includes_schema_and_card_content() -> None:
    prompt = main.build_cursor_review_prompt(
        "Quadratic Discriminant Definition",
        "The discriminant is defined as \\(b^2 - 4ac\\).",
    )

    assert "Return ONLY a JSON object" in prompt
    assert '"title_validity"' in prompt
    assert "Quadratic Discriminant Definition" in prompt
    assert "\\\\(b^2 - 4ac\\\\)" in prompt


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
