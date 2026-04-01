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
        monkeypatch.setattr(config_module, "SETTINGS_DOTENV_PATH", dotenv_file)
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

    settings = config_module.Settings()
    assert (
        settings.app_database_url == "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge"
    )


@pytest.mark.usefixtures("default_settings_sources")
def test_init_values_override_dotenv_and_yaml() -> None:

    settings = config_module.Settings(
        app_db_password="init_secret",
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
        config_module.Settings()
