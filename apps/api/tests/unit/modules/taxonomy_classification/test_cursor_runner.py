"""
Abstract: Unit tests for cursor-runner process invocation and retry behavior.
Out of scope: Parsing cursor payload formats and DB-backed assignment checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from modules.knowledge_graph.dto import TaxonomyClassificationNodeInput
from modules.taxonomy_classification.cursor_runner import CursorClassificationRunner


@dataclass(slots=True)
class _CompletedProcess:
    returncode: int
    stdout: str
    stderr: str


@pytest.mark.anyio
async def test_runner_invokes_cursor_with_single_node_prompt(tmp_path: Path) -> None:
    captured_args: list[str] = []

    def _runner(*, args: list[str], timeout_seconds: float) -> _CompletedProcess:
        captured_args.extend(args)
        assert timeout_seconds == 12.0
        return _CompletedProcess(
            returncode=0,
            stdout="ignored",
            stderr="",
        )

    runner = CursorClassificationRunner(
        command="cursor-agent",
        workspace_root=tmp_path,
        timeout_seconds=12.0,
        max_retries=2,
        session_tool_script=Path("/tmp/taxonomy-classification-session-tool.py"),
        python_executable="/Users/mianqin/Code/knowledge/.venv/bin/python",
        process_runner=_runner,
    )

    await runner.run_node_session(
        node=TaxonomyClassificationNodeInput(
            node_id=42,
            title="Linear Algebra",
            content="Vector spaces and linear maps.",
        )
    )

    joined = " ".join(captured_args)
    assert "--mode ask" not in joined
    assert "Linear Algebra" in captured_args[-1]
    assert "Vector spaces and linear maps." in captured_args[-1]
    assert "/Users/mianqin/Code/knowledge/.venv/bin/python" in captured_args[-1]


@pytest.mark.anyio
async def test_runner_retries_after_non_zero_exit(tmp_path: Path) -> None:
    attempts = 0

    def _runner(*, args: list[str], timeout_seconds: float) -> _CompletedProcess:
        nonlocal attempts
        _ = args
        _ = timeout_seconds
        attempts += 1
        if attempts == 1:
            return _CompletedProcess(returncode=1, stdout="", stderr="transient error")
        return _CompletedProcess(returncode=0, stdout="", stderr="")

    runner = CursorClassificationRunner(
        command="cursor-agent",
        workspace_root=tmp_path,
        timeout_seconds=10.0,
        max_retries=3,
        session_tool_script=Path("/tmp/taxonomy-classification-session-tool.py"),
        process_runner=_runner,
    )

    await runner.run_node_session(
        node=TaxonomyClassificationNodeInput(
            node_id=5,
            title="Thermodynamics",
            content="Energy conservation in closed systems.",
        )
    )

    assert attempts == 2


@pytest.mark.anyio
async def test_runner_raises_after_retries_are_exhausted(tmp_path: Path) -> None:
    def _runner(*, args: list[str], timeout_seconds: float) -> _CompletedProcess:
        _ = args
        _ = timeout_seconds
        return _CompletedProcess(returncode=1, stdout="", stderr="always failing")

    runner = CursorClassificationRunner(
        command="cursor-agent",
        workspace_root=tmp_path,
        timeout_seconds=10.0,
        max_retries=2,
        session_tool_script=Path("/tmp/taxonomy-classification-session-tool.py"),
        process_runner=_runner,
    )

    with pytest.raises(RuntimeError, match="failed after 2 attempts"):
        await runner.run_node_session(
            node=TaxonomyClassificationNodeInput(
                node_id=3,
                title="Optics",
                content="Behavior and properties of light.",
            )
        )
