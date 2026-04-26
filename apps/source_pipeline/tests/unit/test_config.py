"""
Abstract: Unit tests for source-pipeline settings loading.
Out of scope: Database engine creation and runtime queue behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from source_pipeline.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
BASE_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.base.yml"
DEV_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.dev.yml"
PROD_COMPOSE = REPO_ROOT / "infra" / "compose" / "docker-compose.prod.yml"


def _service_block(path: Path, service_name: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    service_header = f"  {service_name}:"
    start = lines.index(service_header)

    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("  ") and not line.startswith("    ") and line.strip():
            break
        block.append(line)

    return block


def test_source_pipeline_settings_require_explicit_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    for field_name in Settings.model_fields:
        monkeypatch.delenv(f"SOURCE_PIPELINE_{field_name.upper()}", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_source_pipeline_settings_require_oauth_job_queue_credentials() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://app:secret@source_pipeline_db:5432/source_pipeline",
        knowledge_api_base_url="http://knowledge-api:8000",
        job_queue_base_url="http://jq.orbitalis.org/api",
        job_queue_token_url="http://jq-logto.orbitalis.org/oidc/token",
        job_queue_client_id="client-id",
        job_queue_client_secret="client-secret",
        job_queue_resource="https://jq-mcp.orbitalis.org",
    )

    assert settings.job_queue_scopes == "jobs:create results:read"
    assert settings.knowledge_api_base_url == "http://knowledge-api:8000"
    assert settings.reconcile_interval_seconds == 3600
    assert settings.reconcile_batch_size == 100


def test_webhook_receiver_role_requires_auth_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "SOURCE_PIPELINE_WEBHOOK_AUTH_ISSUER",
        "SOURCE_PIPELINE_WEBHOOK_AUTH_RESOURCE",
        "SOURCE_PIPELINE_WEBHOOK_AUTH_DISCOVERY_URL",
        "SOURCE_PIPELINE_WEBHOOK_ALLOWED_CLIENT_ID",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError, match="webhook_auth_issuer"):
        Settings(
            role="webhook_receiver",
            database_url="postgresql+psycopg://app:secret@source_pipeline_db:5432/source_pipeline",
        )


def test_webhook_receiver_role_does_not_require_orchestrator_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "SOURCE_PIPELINE_KNOWLEDGE_API_BASE_URL",
        "SOURCE_PIPELINE_JOB_QUEUE_BASE_URL",
        "SOURCE_PIPELINE_JOB_QUEUE_TOKEN_URL",
        "SOURCE_PIPELINE_JOB_QUEUE_CLIENT_ID",
        "SOURCE_PIPELINE_JOB_QUEUE_CLIENT_SECRET",
        "SOURCE_PIPELINE_JOB_QUEUE_RESOURCE",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(
        role="webhook_receiver",
        database_url="postgresql+psycopg://app:secret@source_pipeline_db:5432/source_pipeline",
        webhook_auth_issuer="https://knowledge-logto.example.com/oidc",
        webhook_auth_resource="https://knowledge.example.com/source-pipeline-webhooks",
        webhook_auth_discovery_url="http://logto:3001/oidc/.well-known/openid-configuration",
        webhook_allowed_client_id="job-queue-webhook-delivery",
    )

    assert settings.job_queue_client_secret is None


def test_compose_contains_source_pipeline_webhook_receiver_service() -> None:
    base_block = _service_block(BASE_COMPOSE, "source_pipeline_webhook_receiver")
    dev_block = _service_block(DEV_COMPOSE, "source_pipeline_webhook_receiver")
    stripped_base = [line.strip() for line in base_block]
    stripped_dev = [line.strip() for line in dev_block]

    assert 'command: ["/app/bin/run-webhook-receiver.sh"]' in stripped_base
    assert "SOURCE_PIPELINE_ROLE: webhook_receiver" in stripped_base
    assert any("SOURCE_PIPELINE_WEBHOOK_AUTH_ISSUER" in line for line in stripped_base)
    assert not any("SOURCE_PIPELINE_JOB_QUEUE_CLIENT_SECRET" in line for line in stripped_base)
    assert "ports:" not in stripped_base
    assert 'profiles: ["webhook_receiver"]' in stripped_dev


def test_prod_compose_wires_knowledge_logto_for_webhook_receiver() -> None:
    base_logto_block = _service_block(BASE_COMPOSE, "logto")
    base_receiver_block = _service_block(BASE_COMPOSE, "source_pipeline_webhook_receiver")
    prod_nginx_block = _service_block(PROD_COMPOSE, "nginx")
    stripped_logto = [line.strip() for line in base_logto_block]
    stripped_receiver = [line.strip() for line in base_receiver_block]
    stripped_nginx = [line.strip() for line in prod_nginx_block]

    assert "ENDPOINT: ${KNOWLEDGE_LOGTO_ENDPOINT:-}" in stripped_logto
    assert "logto:" in stripped_receiver
    assert "condition: service_healthy" in stripped_receiver
    assert "- knowledge-logto.orbitalis.org" in stripped_nginx
    assert "- admin.knowledge-logto.internal.home.arpa" in stripped_nginx


def test_compose_contains_explicit_low_frequency_reconcile_settings() -> None:
    base_block = _service_block(BASE_COMPOSE, "orchestrator")
    stripped_base = [line.strip() for line in base_block]

    assert any("SOURCE_PIPELINE_RECONCILE_INTERVAL_SECONDS" in line for line in stripped_base)
    assert any("SOURCE_PIPELINE_RECONCILE_BATCH_SIZE" in line for line in stripped_base)
