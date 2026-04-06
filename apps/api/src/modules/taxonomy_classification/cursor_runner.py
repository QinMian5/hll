"""
Abstract: Cursor-agent runner for one-node taxonomy classification sessions.
Out of scope: Batch selection strategy and taxonomy assignment persistence.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from modules.knowledge_graph.dto import TaxonomyClassificationNodeInput

_CURSOR_MODE_ARGS = [
    "--print",
    "--output-format",
    "json",
    "--force",
    "--sandbox",
    "enabled",
    "--trust",
]


@dataclass(slots=True, frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


def _run_process(*, args: list[str], timeout_seconds: float) -> ProcessResult:
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return ProcessResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _build_prompt(
    *,
    node: TaxonomyClassificationNodeInput,
    session_tool_script: Path,
    python_executable: str,
) -> str:
    tool_command = f"{python_executable} {session_tool_script}"
    return (
        "AUTOMATION MODE.\n"
        "You MUST execute shell commands in this turn. Do not output plans.\n"
        "Classify one knowledge node into the LCC taxonomy.\n"
        "Use ONLY the provided node title and content as semantic context.\n"
        "Traverse taxonomy progressively and choose one final leaf.\n\n"
        "Executable and commands:\n"
        f"1) {tool_command} list-children [--parent-id <int>]\n"
        f"2) {tool_command} get-assignment --node-id <int>\n"
        f"3) {tool_command} assign-leaf --node-id <int> --leaf-id <int>\n\n"
        "Required execution workflow:\n"
        "- Start at root by listing children without parent-id.\n"
        "- Iteratively list children to descend the hierarchy.\n"
        "- Call assign-leaf exactly once for the selected leaf.\n"
        "- If assign-leaf returns already_assigned, keep that existing leaf.\n\n"
        f"Node id: {node.node_id}\n"
        f"Title: {node.title}\n"
        f"Content: {node.content}\n"
    )


class CursorClassificationRunner:
    def __init__(
        self,
        *,
        command: str,
        workspace_root: Path,
        timeout_seconds: float,
        max_retries: int,
        session_tool_script: Path,
        python_executable: str = sys.executable,
        process_runner: Callable[..., ProcessResult] = _run_process,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        self._command = command
        self._workspace_root = workspace_root
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._session_tool_script = session_tool_script
        self._python_executable = python_executable
        self._process_runner = process_runner

    async def run_node_session(
        self,
        *,
        node: TaxonomyClassificationNodeInput,
    ) -> None:
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        prompt = _build_prompt(
            node=node,
            session_tool_script=self._session_tool_script,
            python_executable=self._python_executable,
        )
        args = [
            self._command,
            *_CURSOR_MODE_ARGS,
            "--workspace",
            str(self._workspace_root),
            prompt,
        ]
        last_error: RuntimeError | None = None

        for _ in range(self._max_retries):
            completed = await asyncio.to_thread(
                self._process_runner,
                args=args,
                timeout_seconds=self._timeout_seconds,
            )
            if completed.returncode == 0:
                return
            stderr = completed.stderr.strip() or "no stderr"
            last_error = RuntimeError(
                f"cursor-agent exited with code {completed.returncode}: {stderr}"
            )

        if last_error is None:
            raise RuntimeError("cursor-agent classification failed without detailed error")
        raise RuntimeError(
            f"cursor-agent classification failed after {self._max_retries} attempts"
        ) from last_error
