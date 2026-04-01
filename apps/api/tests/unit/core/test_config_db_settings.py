"""
Abstract: Unit tests for database settings component model and derived URL assembly.
Out of scope: Runtime engine/session lifecycle and migration execution behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

import core.config as config_module

DEFAULT_YAML_CONTENT = "\n".join(
    [
        "# Reserved YAML input channel for future non-secret settings.",
        "# Current DB connection components are sourced from dotenv/init.",
    ]
)

DEFAULT_DOTENV_CONTENT = "\n".join(
    [
        "db_host=postgres",
        "db_port=5432",
        "db_name=knowledge",
        "app_db_user=knowledge_app",
        "app_db_password=secret",
        "migration_db_user=knowledge_migration",
        "migration_db_password=secret_m",
    ]
)


@pytest.fixture
def settings_sources_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[..., tuple[Path, Path]]:
    def _apply(
        *,
        yaml_content: str = DEFAULT_YAML_CONTENT,
        dotenv_content: str = DEFAULT_DOTENV_CONTENT,
    ) -> tuple[Path, Path]:
        settings_yaml = tmp_path / "settings.yaml"
        dotenv_file = tmp_path / ".env.dev"
        settings_yaml.write_text(yaml_content, encoding="utf-8")
        dotenv_file.write_text(dotenv_content, encoding="utf-8")
        monkeypatch.setattr(config_module, "SETTINGS_YAML_PATH", settings_yaml)
        monkeypatch.setenv("SETTINGS_DOTENV_PATH", str(dotenv_file))
        config_module.get_settings.cache_clear()
        return settings_yaml, dotenv_file

    return _apply


@pytest.fixture
def default_settings_sources(
    settings_sources_factory: Callable[..., tuple[Path, Path]],
) -> None:
    settings_sources_factory()


def test_settings_type_is_defined() -> None:
    assert hasattr(
        config_module,
        "Settings",
    ), (
        "core.config.Settings must be defined for component-based "
        "database configuration."
    )


@pytest.mark.usefixtures("default_settings_sources")
def test_build_app_database_url_from_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert hasattr(
        config_module,
        "Settings",
    ), "Settings class is required before URL assembly behavior can be verified."

    monkeypatch.setenv("DB_HOST", "env_should_be_ignored")
    monkeypatch.setenv("APP_DB_PASSWORD", "env_secret_should_be_ignored")

    settings = config_module.Settings.model_validate({})
    assert (
        settings.app_database_url
        == "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge"
    )


@pytest.mark.usefixtures("default_settings_sources")
def test_init_values_override_dotenv_and_yaml() -> None:
    settings = config_module.Settings.model_validate(
        {"app_db_password": "init_secret"},
    )

    assert (
        settings.app_database_url
        == "postgresql+psycopg://knowledge_app:init_secret@postgres:5432/knowledge"
    )


def test_settings_require_all_components_without_defaults(
    settings_sources_factory: Callable[..., tuple[Path, Path]],
) -> None:
    settings_sources_factory(
        dotenv_content="\n".join(
            [
                "app_db_password=secret",
            ]
        )
    )

    with pytest.raises(ValidationError):
        config_module.Settings.model_validate({})


def test_settings_reject_unsupported_dotenv_keys(
    settings_sources_factory: Callable[..., tuple[Path, Path]],
) -> None:
    settings_sources_factory(
        dotenv_content="\n".join(
            [
                DEFAULT_DOTENV_CONTENT,
                "UNEXPECTED_KEY=boom",
            ]
        )
    )

    with pytest.raises(ValidationError, match="unexpected_key"):
        config_module.Settings.model_validate({})


def test_settings_require_explicit_dotenv_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SETTINGS_DOTENV_PATH", raising=False)
    config_module.get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SETTINGS_DOTENV_PATH"):
        config_module.Settings.model_validate({})


def test_settings_raise_when_configured_dotenv_file_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.env"
    monkeypatch.setenv("SETTINGS_DOTENV_PATH", str(missing_path))
    config_module.get_settings.cache_clear()

    with pytest.raises(FileNotFoundError, match="does not exist"):
        config_module.Settings.model_validate({})


@pytest.mark.usefixtures("default_settings_sources")
def test_validate_test_database_settings_accepts_isolated_test_target() -> None:
    settings = config_module.Settings.model_validate({})
    settings.db_host = "127.0.0.1"
    settings.db_name = "knowledge_test"
    settings.app_db_user = "knowledge_app_test"
    settings.migration_db_user = "knowledge_migration_test"

    config_module.validate_test_database_settings(
        settings,
        allowed_hosts={"localhost", "127.0.0.1"},
    )


@pytest.mark.usefixtures("default_settings_sources")
def test_validate_test_database_settings_rejects_non_test_database_name() -> None:
    settings = config_module.Settings.model_validate({})
    settings.db_host = "127.0.0.1"
    settings.app_db_user = "knowledge_app_test"
    settings.migration_db_user = "knowledge_migration_test"

    settings.db_name = "knowledge"
    with pytest.raises(ValueError, match="DB_NAME must end with '_test'"):
        config_module.validate_test_database_settings(
            settings,
            allowed_hosts={"localhost", "127.0.0.1"},
        )


@pytest.mark.usefixtures("default_settings_sources")
def test_validate_test_database_settings_rejects_host_outside_allowlist() -> None:
    settings = config_module.Settings.model_validate({})

    settings.db_name = "knowledge_test"
    settings.app_db_user = "knowledge_app_test"
    settings.migration_db_user = "knowledge_migration_test"
    settings.db_host = "db.internal.prod"
    with pytest.raises(ValueError, match="DB_HOST must be one of"):
        config_module.validate_test_database_settings(
            settings,
            allowed_hosts={"localhost", "127.0.0.1"},
        )


@pytest.mark.usefixtures("default_settings_sources")
def test_validate_test_database_settings_rejects_non_test_role_names() -> None:
    settings = config_module.Settings.model_validate({})
    settings.db_host = "127.0.0.1"
    settings.db_name = "knowledge_test"

    with pytest.raises(ValueError, match="APP_DB_USER must end with '_test'"):
        config_module.validate_test_database_settings(
            settings,
            allowed_hosts={"localhost", "127.0.0.1"},
        )


def test_get_settings_does_not_mix_test_guardrails_into_runtime_loader(
    settings_sources_factory: Callable[..., tuple[Path, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_sources_factory()
    monkeypatch.setenv("APP_ENV", "test")
    config_module.get_settings.cache_clear()

    try:
        settings = config_module.get_settings()
        assert settings.db_name == "knowledge"
    finally:
        config_module.get_settings.cache_clear()
