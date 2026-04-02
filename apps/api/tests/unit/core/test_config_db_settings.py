"""
Abstract: Unit tests for env-file-backed settings and derived URL assembly.
Out of scope: Runtime engine/session lifecycle and migration execution behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

import core.config as config_module

DEFAULT_DOTENV_CONTENT = "\n".join(
    [
        "DB_HOST=postgres",
        "DB_PORT=5432",
        "DB_NAME=knowledge",
        "APP_DB_USER=knowledge_app",
        "APP_DB_PASSWORD=secret",
        "MIGRATION_DB_USER=knowledge_migration",
        "MIGRATION_DB_PASSWORD=secret_m",
        "REDIS_URL=redis://redis:6379/0",
        "EMBEDDING_API_URL=https://api.openai.com/v1/embeddings",
        "EMBEDDING_MODEL=text-embedding-3-small",
        "EMBEDDING_API_KEY=test-key",
        "EMBEDDING_TIMEOUT_SECONDS=10",
        "SEARCH_MAX_MATCHED=5",
        "SEARCH_MAX_CONNECTED=10",
        "EDGE_SIMILARITY_TOP_K=10",
        "EDGE_SIMILARITY_MIN_STRENGTH=0.6",
        "LOG_FILE_PATH=logs/api/app.log",
    ]
)


@pytest.fixture
def dotenv_file_factory(
    tmp_path: Path,
) -> Callable[[str], Path]:
    def _build(dotenv_content: str = DEFAULT_DOTENV_CONTENT) -> Path:
        dotenv_file = tmp_path / ".env.runtime"
        dotenv_file.write_text(dotenv_content, encoding="utf-8")
        return dotenv_file

    return _build


def test_settings_type_is_defined() -> None:
    assert hasattr(
        config_module,
        "Settings",
    ), (
        "core.config.Settings must be defined for component-based "
        "database configuration."
    )


def test_build_app_database_url_from_components(
    dotenv_file_factory: Callable[[str], Path],
) -> None:
    settings = config_module.Settings(_env_file=dotenv_file_factory())
    assert (
        settings.app_database_url
        == "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge"
    )


def test_init_values_override_env_file(
    dotenv_file_factory: Callable[[str], Path],
) -> None:
    settings = config_module.Settings(
        _env_file=dotenv_file_factory(),
        app_db_password="init_secret",
    )
    assert (
        settings.app_database_url
        == "postgresql+psycopg://knowledge_app:init_secret@postgres:5432/knowledge"
    )


def test_settings_require_all_components_without_defaults(
    dotenv_file_factory: Callable[[str], Path],
) -> None:
    dotenv_file = dotenv_file_factory(
        dotenv_content="\n".join(
            [
                "APP_DB_PASSWORD=secret",
            ]
        )
    )
    with pytest.raises(ValidationError):
        config_module.Settings(_env_file=dotenv_file)


def test_settings_require_log_file_path(
    dotenv_file_factory: Callable[[str], Path],
) -> None:
    filtered_lines = [
        line
        for line in DEFAULT_DOTENV_CONTENT.splitlines()
        if not line.startswith("LOG_FILE_PATH=")
    ]
    dotenv_file = dotenv_file_factory(dotenv_content="\n".join(filtered_lines))
    with pytest.raises(ValidationError, match="log_file_path"):
        config_module.Settings(_env_file=dotenv_file)


def test_settings_apply_logging_defaults_when_optional_keys_absent(
    dotenv_file_factory: Callable[[str], Path],
) -> None:
    dotenv_file = dotenv_file_factory(
        dotenv_content=DEFAULT_DOTENV_CONTENT,
    )
    settings = config_module.Settings(_env_file=dotenv_file)
    assert settings.log_level == "INFO"
    assert settings.log_file_max_bytes == 10_485_760
    assert settings.log_file_backup_count == 5


def test_load_settings_resolves_logging_fields_from_tracked_test_env(
    repo_root: Path,
) -> None:
    settings = config_module.Settings(
        _env_file=repo_root / "infra" / "env" / ".env.test"
    )
    assert settings.log_file_path.strip()
    assert settings.log_level == "INFO"
    assert settings.log_file_max_bytes == 10_485_760
    assert settings.log_file_backup_count == 5


def test_settings_reject_unsupported_dotenv_keys(
    dotenv_file_factory: Callable[[str], Path],
) -> None:
    dotenv_file = dotenv_file_factory(
        dotenv_content="\n".join(
            [
                DEFAULT_DOTENV_CONTENT,
                "UNEXPECTED_KEY=boom",
            ]
        )
    )
    with pytest.raises(ValidationError, match="unexpected_key"):
        config_module.Settings(_env_file=dotenv_file)


def test_settings_raise_when_configured_dotenv_file_missing(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.env"
    with pytest.raises(ValidationError, match="db_host"):
        config_module.Settings(_env_file=missing_path)
