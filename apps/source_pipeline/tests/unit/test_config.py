"""
Abstract: Unit tests for source-pipeline settings loading.
Out of scope: Database engine creation and runtime queue behavior.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from source_pipeline.config import Settings


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
