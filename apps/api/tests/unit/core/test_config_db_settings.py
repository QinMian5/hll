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
    "KNOWLEDGE_API_SEARCH_MAX_MATCHED": "5",
    "KNOWLEDGE_API_SEARCH_MAX_CONNECTED": "10",
    "KNOWLEDGE_API_EDGE_SIMILARITY_TOP_K": "10",
    "KNOWLEDGE_API_EDGE_SIMILARITY_MIN_STRENGTH": "0.37",
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


def test_load_settings_reads_edge_similarity_threshold_from_environment(
    isolated_env: pytest.MonkeyPatch,
) -> None:
    _set_env(
        isolated_env,
        RUNTIME_REQUIRED_ENV | {"KNOWLEDGE_API_EDGE_SIMILARITY_MIN_STRENGTH": "0.83"},
    )
    settings = config_module.Settings()
    assert settings.edge_similarity_min_strength == 0.83


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
