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
    "KNOWLEDGE_API_SEARCH_VECTOR_CANDIDATE_POOL_SIZE": "64",
    "KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K": "2",
    "KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K": "4",
    "KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH": "0.61",
    "KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT": "9",
    "KNOWLEDGE_API_SEARCH_RESPONSE_CACHE_TTL_SECONDS": "60",
    "KNOWLEDGE_API_SEARCH_EMBEDDING_CACHE_TTL_SECONDS": "86400",
    "KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS": "60",
    "KNOWLEDGE_API_LOG_LEVEL": "INFO",
    "KNOWLEDGE_API_LOG_FILE_PATH": "logs/api/app.log",
    "KNOWLEDGE_API_LOG_FILE_MAX_BYTES": "10485760",
    "KNOWLEDGE_API_LOG_FILE_BACKUP_COUNT": "5",
    "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_COMMAND": "cursor-agent",
    "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_WORKSPACE_ROOT": (
        "/tmp/knowledge-api-taxonomy-classification"
    ),
    "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_TIMEOUT_SECONDS": "180",
    "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_MAX_RETRIES": "3",
    "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_MAX_WORKERS": "8",
}

MIGRATION_REQUIRED_ENV = {
    "KNOWLEDGE_API_MIGRATION_DATABASE_URL": "postgresql+psycopg://knowledge_migration:secret@postgres:5432/knowledge",
}

ALL_SETTINGS_KEYS = (
    set(RUNTIME_REQUIRED_ENV)
    | set(MIGRATION_REQUIRED_ENV)
    | {
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
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_REQUEST_BATCH_SIZE",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_FLUSH_INTERVAL_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_PROJECTION_REFRESH_BATCH_SIZE",
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


@pytest.mark.parametrize(
    "settings_type",
    (
        config_module.Settings,
        config_module.TaxonomyClassificationRuntimeSettings,
        config_module.TaxonomyViewLayoutRuntimeSettings,
        config_module.TaxonomyClassificationWebhookReceiverSettings,
    ),
)
def test_runtime_settings_do_not_define_code_defaults(settings_type: type) -> None:
    assert all(field.is_required() for field in settings_type.model_fields.values())


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


def test_load_settings_reads_search_vector_candidate_pool_size_from_environment(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        RUNTIME_REQUIRED_ENV
        | {"KNOWLEDGE_API_SEARCH_VECTOR_CANDIDATE_POOL_SIZE": "32"},
    )
    settings = config_module.Settings()
    assert settings.search_vector_candidate_pool_size == 32


def test_load_settings_rejects_search_vector_candidate_pool_below_max_matched(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        RUNTIME_REQUIRED_ENV
        | {
            "KNOWLEDGE_API_SEARCH_MAX_MATCHED": "6",
            "KNOWLEDGE_API_SEARCH_VECTOR_CANDIDATE_POOL_SIZE": "5",
        },
    )
    with pytest.raises(ValidationError, match="search_vector_candidate_pool_size"):
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


def test_load_settings_requires_logging_keys(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    values = dict(RUNTIME_REQUIRED_ENV)
    values.pop("KNOWLEDGE_API_LOG_LEVEL")
    _set_env(isolated_env, values)
    with pytest.raises(ValidationError, match="log_level"):
        config_module.Settings()


def test_load_settings_requires_cache_ttl_keys(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    values = dict(RUNTIME_REQUIRED_ENV)
    values.pop("KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS")
    _set_env(isolated_env, values)
    with pytest.raises(ValidationError, match="taxonomy_view_cache_ttl_seconds"):
        config_module.Settings()


def test_load_settings_reads_cache_ttls_from_environment(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        RUNTIME_REQUIRED_ENV
        | {
            "KNOWLEDGE_API_SEARCH_RESPONSE_CACHE_TTL_SECONDS": "45",
            "KNOWLEDGE_API_SEARCH_EMBEDDING_CACHE_TTL_SECONDS": "7200",
            "KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS": "30",
        },
    )
    settings = config_module.Settings()
    assert settings.search_response_cache_ttl_seconds == 45
    assert settings.search_embedding_cache_ttl_seconds == 7200
    assert settings.taxonomy_view_cache_ttl_seconds == 30


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
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_SCOPES": "jobs:create results:read",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_INTERVAL_SECONDS": "5",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_BATCH_SIZE": "100",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_INTERVAL_SECONDS": "3600",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_BATCH_SIZE": "100",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_REQUEST_BATCH_SIZE": "2",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_FLUSH_INTERVAL_SECONDS": "60",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_PROJECTION_REFRESH_BATCH_SIZE": "1",
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
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME": "taxonomy_classification",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_SCOPES": "jobs:create results:read",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_INTERVAL_SECONDS": "5",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_BATCH_SIZE": "100",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_INTERVAL_SECONDS": "3600",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_BATCH_SIZE": "100",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_REQUEST_BATCH_SIZE": "2",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_FLUSH_INTERVAL_SECONDS": "60",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_PROJECTION_REFRESH_BATCH_SIZE": "1",
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
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME": "taxonomy_classification",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_HTTP_TIMEOUT_SECONDS": "5",
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
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME": "taxonomy_classification",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_JOB_QUEUE_SCOPES": "jobs:create results:read",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_INTERVAL_SECONDS": "5",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_POLL_BATCH_SIZE": "100",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_INTERVAL_SECONDS": "3600",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_RECONCILE_BATCH_SIZE": "100",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_REQUEST_BATCH_SIZE": "2",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CONTINUATION_FLUSH_INTERVAL_SECONDS": "60",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_PROJECTION_REFRESH_BATCH_SIZE": "1",
        },
    )

    settings = config_module.TaxonomyClassificationRuntimeSettings()

    assert settings.taxonomy_classification_queue_name == "taxonomy_classification"
    assert settings.taxonomy_classification_job_queue_client_secret == "runtime-secret"
    assert settings.taxonomy_classification_continuation_request_batch_size == 2
    assert settings.taxonomy_classification_continuation_flush_interval_seconds == 60
    assert settings.taxonomy_classification_projection_refresh_batch_size == 1


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
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_QUEUE_NAME": "taxonomy_classification",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_AUTH_HTTP_TIMEOUT_SECONDS": "5",
            "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_WEBHOOK_PUBLIC_PATH": (
                "/taxonomy-classification/webhooks/job-queue"
            ),
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
