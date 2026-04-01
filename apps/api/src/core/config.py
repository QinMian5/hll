"""
Abstract: Minimal settings entrypoint using init + explicit dotenv path
with optional infra yaml fallback.
Out of scope: Request-scoped dependency injection and
SQLAlchemy session lifecycle wiring.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SETTINGS_YAML_PATH = PROJECT_ROOT / "infra" / "config" / "settings.yaml"
SETTINGS_DOTENV_PATH_ENV_VAR = "SETTINGS_DOTENV_PATH"
DEFAULT_TEST_ALLOWED_DB_HOSTS = frozenset({"localhost", "127.0.0.1"})


def _resolve_dotenv_path() -> Path | None:
    raw_dotenv_path = os.getenv(SETTINGS_DOTENV_PATH_ENV_VAR)
    if not raw_dotenv_path:
        return None
    return Path(raw_dotenv_path).expanduser()


def _require_dotenv_path() -> Path:
    dotenv_path = _resolve_dotenv_path()
    if dotenv_path is None:
        raise RuntimeError(
            f"{SETTINGS_DOTENV_PATH_ENV_VAR} is not configured. "
            "Set an explicit dotenv file path before loading Settings."
        )

    if not dotenv_path.exists():
        raise FileNotFoundError(
            f"Configured settings dotenv file does not exist: {dotenv_path}"
        )

    return dotenv_path


def _build_postgres_url(
    *,
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    encoded_user = quote(user, safe="")
    encoded_password = quote(password, safe="")
    encoded_host = quote(host, safe="")
    encoded_database = quote(database, safe="")
    return f"postgresql+psycopg://{encoded_user}:{encoded_password}@{encoded_host}:{port}/{encoded_database}"


def validate_test_database_settings(
    settings: Settings,
    *,
    allowed_hosts: set[str] | frozenset[str] = DEFAULT_TEST_ALLOWED_DB_HOSTS,
) -> None:
    if not settings.db_name.endswith("_test"):
        raise ValueError("DB_NAME must end with '_test' in test environment.")

    if settings.db_host not in allowed_hosts:
        expected_hosts = ", ".join(sorted(allowed_hosts))
        raise ValueError(
            f"DB_HOST must be one of [{expected_hosts}] in test environment."
        )

    if not settings.app_db_user.endswith("_test"):
        raise ValueError("APP_DB_USER must end with '_test' in test environment.")

    if not settings.migration_db_user.endswith("_test"):
        raise ValueError("MIGRATION_DB_USER must end with '_test' in test environment.")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid",
        case_sensitive=False,
    )

    db_host: str
    db_port: int
    db_name: str
    app_db_user: str
    app_db_password: str
    migration_db_user: str
    migration_db_password: str

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Keep framework-defined signature names for keyword compatibility.
        return (
            init_settings,
            DotEnvSettingsSource(
                settings_cls,
                env_file=_require_dotenv_path(),
                env_file_encoding="utf-8",
            ),
            YamlConfigSettingsSource(
                settings_cls,
                yaml_file=SETTINGS_YAML_PATH,
                yaml_file_encoding="utf-8",
            ),
        )

    @property
    def app_database_url(self) -> str:
        return _build_postgres_url(
            user=self.app_db_user,
            password=self.app_db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def migration_database_url(self) -> str:
        return _build_postgres_url(
            user=self.migration_db_user,
            password=self.migration_db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.model_validate({})
