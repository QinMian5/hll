"""
Abstract: Unit tests for runtime and migration settings loaded from process environment.
Out of scope: Runtime engine/session lifecycle and migration execution behavior.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import core.config as config_module

RUNTIME_REQUIRED_ENV = {
    "KNOWLEDGE_API_DATABASE_URL": "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge",
    "KNOWLEDGE_API_REDIS_URL": "redis://redis:6379/0",
    "KNOWLEDGE_API_EMBEDDING_API_URL": "https://api.openai.com/v1/embeddings",
    "KNOWLEDGE_API_EMBEDDING_MODEL": "text-embedding-3-small",
    "KNOWLEDGE_API_EMBEDDING_API_KEY": "test-key",
    "KNOWLEDGE_API_EMBEDDING_TIMEOUT_SECONDS": "10",
    "KNOWLEDGE_API_SEARCH_MAX_MATCHED": "3",
    "KNOWLEDGE_API_SEARCH_MAX_CONNECTED": "7",
    "KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K": "2",
    "KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K": "4",
    "KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH": "0.61",
    "KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT": "9",
    "KNOWLEDGE_API_LOG_FILE_PATH": "logs/api/app.log",
}

MIGRATION_REQUIRED_ENV = {
    "KNOWLEDGE_API_MIGRATION_DATABASE_URL": "postgresql+psycopg://knowledge_migration:secret@postgres:5432/knowledge",
}

ALL_SETTINGS_KEYS = (
    set(RUNTIME_REQUIRED_ENV)
    | set(MIGRATION_REQUIRED_ENV)
    | {
        "KNOWLEDGE_API_LOG_LEVEL",
        "KNOWLEDGE_API_LOG_FILE_MAX_BYTES",
        "KNOWLEDGE_API_LOG_FILE_BACKUP_COUNT",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_COMMAND",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_WORKSPACE_ROOT",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_TIMEOUT_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_MAX_RETRIES",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_MAX_WORKERS",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_BASE_URL",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_TOKEN_URL",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_ID",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_RESOURCE",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_SCOPES",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_ISSUER",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_RESOURCE",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_DISCOVERY_URL",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_HTTP_TIMEOUT_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_PUBLIC_PATH",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_INTERVAL_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_BATCH_SIZE",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_INTERVAL_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_BATCH_SIZE",
        "AN_UNRELATED_KEY",
    }
)


def _set_env(
    monkeypatch: pytest.MonkeyPatch,
    values: dict[str, str],
) -> None:
    for key, value in values.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key in ALL_SETTINGS_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_settings_type_is_defined() -> None:
    assert hasattr(config_module, "Settings")


def test_migration_settings_type_is_defined() -> None:
    assert hasattr(config_module, "MigrationSettings")


def test_load_settings_reads_database_url_from_environment(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(isolated_env, RUNTIME_REQUIRED_ENV)
    settings = config_module.Settings()
    assert (
        settings.database_url == "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge"
    )


def test_load_settings_reads_edge_initialization_policy_from_environment(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        RUNTIME_REQUIRED_ENV
        | {
            "KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K": "0",
            "KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K": "5",
            "KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH": "0.83",
            "KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT": "11",
        },
    )
    settings = config_module.Settings()
    assert settings.edge_title_mention_top_k == 0
    assert settings.edge_semantic_top_k == 5
    assert settings.edge_semantic_min_strength == 0.83
    assert settings.edge_semantic_candidate_limit == 11


def test_load_settings_rejects_semantic_candidate_limit_below_semantic_top_k(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        RUNTIME_REQUIRED_ENV
        | {
            "KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K": "5",
            "KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT": "4",
        },
    )
    with pytest.raises(ValidationError, match="edge_semantic_candidate_limit"):
        config_module.Settings()


def test_load_settings_requires_database_url(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    values = dict(RUNTIME_REQUIRED_ENV)
    values.pop("KNOWLEDGE_API_DATABASE_URL")
    _set_env(isolated_env, values)
    with pytest.raises(ValidationError, match="database_url"):
        config_module.Settings()


def test_load_settings_requires_log_file_path(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    values = dict(RUNTIME_REQUIRED_ENV)
    values.pop("KNOWLEDGE_API_LOG_FILE_PATH")
    _set_env(isolated_env, values)
    with pytest.raises(ValidationError, match="log_file_path"):
        config_module.Settings()


def test_load_settings_ignores_unrelated_infra_keys(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(isolated_env, RUNTIME_REQUIRED_ENV | {"AN_UNRELATED_KEY": "allowed"})
    settings = config_module.Settings()
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_load_settings_applies_logging_defaults_when_optional_keys_absent(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(isolated_env, RUNTIME_REQUIRED_ENV)
    settings = config_module.Settings()
    assert settings.log_level == "INFO"
    assert settings.log_file_max_bytes == 10_485_760
    assert settings.log_file_backup_count == 5


def test_shared_settings_exclude_taxonomy_classification_job_queue_and_webhook_fields(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        RUNTIME_REQUIRED_ENV
        | {
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME": "taxonomy_classification",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_BASE_URL": "http://job-queue/api",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_TOKEN_URL": "http://logto/oidc/token",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_ID": "taxonomy-runtime",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET": "runtime-secret",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_RESOURCE": "https://job-queue",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID": (
                "job-queue-delivery"
            ),
        },
    )

    settings = config_module.Settings()

    assert not hasattr(settings, "taxonomy_classification_queue_name")
    assert not hasattr(settings, "taxonomy_classification_job_queue_client_secret")
    assert not hasattr(settings, "taxonomy_classification_webhook_allowed_client_id")


def test_taxonomy_classification_runtime_settings_require_job_queue_secret(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        {
            "KNOWLEDGE_API_DATABASE_URL": RUNTIME_REQUIRED_ENV["KNOWLEDGE_API_DATABASE_URL"],
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_BASE_URL": "http://job-queue/api",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_TOKEN_URL": "http://logto/oidc/token",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_ID": "taxonomy-runtime",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_RESOURCE": "https://job-queue",
        },
    )

    with pytest.raises(ValidationError, match="job_queue_client_secret"):
        config_module.TaxonomyClassificationRuntimeSettings()


def test_taxonomy_classification_webhook_settings_do_not_expose_job_queue_secret(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        {
            "KNOWLEDGE_API_DATABASE_URL": RUNTIME_REQUIRED_ENV["KNOWLEDGE_API_DATABASE_URL"],
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_ISSUER": "https://knowledge-logto",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_RESOURCE": "https://knowledge-api",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_DISCOVERY_URL": "http://logto/.well-known/openid-configuration",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID": "job-queue-delivery",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_PUBLIC_PATH": (
                "/taxonomy-classification/webhooks/job-queue"
            ),
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET": "runtime-secret",
        },
    )

    settings = config_module.TaxonomyClassificationWebhookReceiverSettings()

    assert settings.taxonomy_classification_webhook_allowed_client_id == "job-queue-delivery"
    assert not hasattr(settings, "taxonomy_classification_job_queue_client_secret")


def test_taxonomy_classification_runtime_settings_are_role_scoped(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        {
            "KNOWLEDGE_API_DATABASE_URL": RUNTIME_REQUIRED_ENV["KNOWLEDGE_API_DATABASE_URL"],
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_BASE_URL": "http://job-queue/api",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_TOKEN_URL": "http://logto/oidc/token",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_ID": "taxonomy-runtime",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_CLIENT_SECRET": "runtime-secret",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_RESOURCE": "https://job-queue",
        },
    )

    settings = config_module.TaxonomyClassificationRuntimeSettings()

    assert settings.taxonomy_classification_queue_name == "taxonomy_classification"
    assert settings.taxonomy_classification_job_queue_client_secret == "runtime-secret"


def test_taxonomy_classification_webhook_receiver_settings_are_role_scoped(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        {
            "KNOWLEDGE_API_DATABASE_URL": RUNTIME_REQUIRED_ENV["KNOWLEDGE_API_DATABASE_URL"],
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_ISSUER": "https://knowledge-logto",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_RESOURCE": "https://knowledge-api",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_DISCOVERY_URL": "http://logto/oidc/.well-known/openid-configuration",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_ALLOWED_CLIENT_ID": "delivery",
        },
    )

    settings = config_module.TaxonomyClassificationWebhookReceiverSettings()

    assert settings.taxonomy_classification_webhook_allowed_client_id == "delivery"
    assert not hasattr(settings, "taxonomy_classification_job_queue_client_secret")


def test_load_settings_from_process_environment_only(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(isolated_env, RUNTIME_REQUIRED_ENV | {"KNOWLEDGE_API_LOG_LEVEL": "DEBUG"})
    settings = config_module.Settings()
    assert settings.log_file_path.strip()
    assert settings.log_level == "DEBUG"
    assert settings.log_file_max_bytes == 10_485_760
    assert settings.log_file_backup_count == 5


def test_load_migration_settings_reads_database_url_from_environment(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(isolated_env, MIGRATION_REQUIRED_ENV)
    settings = config_module.MigrationSettings()
    assert (
        settings.database_url
        == "postgresql+psycopg://knowledge_migration:secret@postgres:5432/knowledge"
    )


def test_load_migration_settings_requires_database_url(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationError, match="database_url"):
        config_module.MigrationSettings()
