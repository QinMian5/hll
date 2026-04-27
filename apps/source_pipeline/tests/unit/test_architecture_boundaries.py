"""
Abstract: Static boundary tests for source-pipeline architecture constraints.
Out of scope: Runtime integration behavior and API module boundary checks.
"""

from __future__ import annotations

from pathlib import Path

from source_pipeline.pipeline_webhook.auth import WebhookAuthVerifier as SourceWebhookAuthVerifier

SOURCE_PIPELINE_SRC = Path(__file__).resolve().parents[2] / "src" / "source_pipeline"


def _python_sources() -> list[Path]:
    return sorted(SOURCE_PIPELINE_SRC.rglob("*.py"))


def test_source_pipeline_does_not_import_api_internal_modules() -> None:
    forbidden_fragments = (
        "from core",
        "import core",
        "from modules.",
        "import modules.",
        "from entrypoints.",
        "import entrypoints.",
        "apps.api",
    )

    violations: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in text:
                violations.append(f"{path.relative_to(SOURCE_PIPELINE_SRC)}: {fragment}")

    assert violations == []


def test_source_pipeline_does_not_write_knowledge_graph_tables_directly() -> None:
    forbidden_fragments = (
        "knowledge_graph",
        "INSERT INTO nodes",
        "INSERT INTO edges",
        "UPDATE nodes",
        "UPDATE edges",
        "DELETE FROM nodes",
        "DELETE FROM edges",
    )

    violations: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in text:
                violations.append(f"{path.relative_to(SOURCE_PIPELINE_SRC)}: {fragment}")

    assert violations == []


def test_source_pipeline_uses_direct_job_queue_sdk_without_local_integration_package() -> None:
    violations: list[str] = []
    sdk_references: list[str] = []
    forbidden_package = "job_queue" + "_integration"
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(SOURCE_PIPELINE_SRC)
        if forbidden_package in text:
            violations.append(str(relative_path))
        if "job_queue_mcp_client" in text:
            sdk_references.append(str(relative_path))

    assert violations == []
    assert "pipeline_runtime/service.py" in sdk_references
    assert "entrypoints/orchestrator.py" in sdk_references
    assert SourceWebhookAuthVerifier.__module__ == "source_pipeline.pipeline_webhook.auth"
