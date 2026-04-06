from __future__ import annotations

import subprocess

import pytest

from wiki_page_to_cards_cursor import (
    PageAgentSettings,
    run_page_session,
)
from wiki_page_to_cards_types import PageRecord


def test_run_page_session_returns_page_result_from_cursor_payload(
    monkeypatch: pytest.MonkeyPatch,
    sample_page: PageRecord,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"type":"result","result":"{\\"page_id\\":42,\\"completed\\":true,\\"reason\\":null}"}',
            stderr="",
        ),
    )

    result = run_page_session(
        sample_page,
        settings=PageAgentSettings(
            cursor_agent_workspace_root="/tmp/wiki-page-to-cards-tests"
        ),
    )

    assert result.page_id == 42
    assert result.completed is True
    assert result.reason is None


def test_run_page_session_returns_failure_reason_from_cursor_payload(
    monkeypatch: pytest.MonkeyPatch,
    sample_page: PageRecord,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"type":"result","result":"{\\"page_id\\":42,\\"completed\\":false,\\"reason\\":\\"The page agent could not revise a rejected candidate into a valid card.\\"}"}',
            stderr="",
        ),
    )

    result = run_page_session(
        sample_page,
        settings=PageAgentSettings(
            cursor_agent_workspace_root="/tmp/wiki-page-to-cards-tests"
        ),
    )

    assert result.page_id == 42
    assert result.completed is False
    assert (
        result.reason
        == "The page agent could not revise a rejected candidate into a valid card."
    )


def test_run_page_session_invokes_cursor_agent_with_existing_write_card_command(
    monkeypatch: pytest.MonkeyPatch,
    sample_page: PageRecord,
) -> None:
    seen_args: list[str] = []

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        nonlocal seen_args
        seen_args = list(args[0])
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='{"type":"result","result":"{\\"page_id\\":42,\\"completed\\":true,\\"reason\\":null}"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_page_session(
        sample_page,
        settings=PageAgentSettings(
            cursor_agent_workspace_root="/tmp/wiki-page-to-cards-tests"
        ),
    )

    assert seen_args[0] == "cursor-agent"
    assert "--print" in seen_args
    assert "--output-format" in seen_args
    assert "--force" in seen_args
    assert "--sandbox" in seen_args
