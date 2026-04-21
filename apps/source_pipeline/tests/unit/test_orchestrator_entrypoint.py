"""
Abstract: Unit tests for the source-pipeline orchestrator bootstrap.
Out of scope: Runtime state transitions and Docker image build behavior.
"""

from __future__ import annotations

from pathlib import Path

from source_pipeline.entrypoints import orchestrator as module


def test_orchestrator_entrypoint_builds_runtime_once(monkeypatch) -> None:
    calls: list[object] = []
    runtime = object()
    monkeypatch.setattr(module, "build_runtime", lambda: runtime)

    async def fake_run_forever(runtime_obj: object) -> None:
        calls.append(runtime_obj)

    monkeypatch.setattr(module, "run_forever", fake_run_forever)

    module.main()

    assert calls == [runtime]


def test_compose_contains_orchestrator_service() -> None:
    compose = Path(
        "/Users/mianqin/Code/knowledge/.worktrees/source-pipeline-orchestrator/"
        "infra/compose/docker-compose.base.yml"
    ).read_text()

    assert "source_pipeline_migrate:" in compose
    assert "orchestrator:" in compose
    assert "run-orchestrator.sh" in compose
