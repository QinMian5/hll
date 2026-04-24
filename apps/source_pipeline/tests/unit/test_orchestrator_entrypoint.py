"""
Abstract: Unit tests for the source-pipeline orchestrator bootstrap.
Out of scope: Runtime state transitions and Docker image build behavior.
"""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from source_pipeline.config import Settings
from source_pipeline.entrypoints import orchestrator as module
from source_pipeline.pipeline_handoff.knowledge_ingestion import KnowledgeIngestionHandoff


def test_orchestrator_entrypoint_builds_runtime_once(monkeypatch: MonkeyPatch) -> None:
    calls: list[object] = []
    runtime = object()
    monkeypatch.setattr(module, "build_runtime", lambda: runtime)

    async def fake_run_forever(runtime_obj: object) -> None:
        calls.append(runtime_obj)

    monkeypatch.setattr(module, "run_forever", fake_run_forever)

    module.main()

    assert calls == [runtime]


def test_compose_contains_orchestrator_service() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    compose = (repo_root / "infra/compose/docker-compose.base.yml").read_text()

    assert "source_pipeline_migrate:" in compose
    assert "orchestrator:" in compose
    assert "run-orchestrator.sh" in compose


def test_build_runtime_wires_knowledge_ingestion_handoff(monkeypatch: MonkeyPatch) -> None:
    settings = Settings(
        database_url="postgresql+psycopg://app:secret@source_pipeline_db:5432/source_pipeline",
        knowledge_api_base_url="http://knowledge-api:8000",
        job_queue_base_url="http://jq.orbitalis.org/api",
        job_queue_token_url="http://jq-logto.orbitalis.org/oidc/token",
        job_queue_client_id="client-id",
        job_queue_client_secret="client-secret",
        job_queue_resource="https://jq-mcp.orbitalis.org",
    )
    engine = object()
    session_factory = object()

    monkeypatch.setattr(module, "load_settings", lambda: settings)
    monkeypatch.setattr(
        module,
        "build_session_factory",
        lambda runtime_settings: (engine, session_factory),
    )

    runtime = module.build_runtime()

    assert runtime.settings is settings
    assert runtime.engine is engine
    assert runtime.session_factory is session_factory
    assert isinstance(runtime.card_handoff, KnowledgeIngestionHandoff)
