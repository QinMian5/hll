"""
Abstract: Static boundary tests for source-pipeline architecture constraints.
Out of scope: Runtime integration behavior and API module boundary checks.
"""

from __future__ import annotations

from pathlib import Path

from job_queue_integration.client import JobQueueClient
from job_queue_integration.token import ClientCredentialsTokenProvider
from job_queue_integration.webhook_auth import WebhookAuthVerifier

from source_pipeline.pipeline_runtime.job_queue_client import JobQueueClient as SourceJobQueueClient
from source_pipeline.pipeline_runtime.job_queue_token import (
    ClientCredentialsTokenProvider as SourceTokenProvider,
)
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


def test_source_pipeline_reuses_shared_job_queue_helpers() -> None:
    assert SourceJobQueueClient is JobQueueClient
    assert SourceTokenProvider is ClientCredentialsTokenProvider
    assert SourceWebhookAuthVerifier is WebhookAuthVerifier
