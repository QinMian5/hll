"""
Abstract: Minimal settings entrypoint using init + infra dotenv
with optional infra yaml fallback.
Out of scope: Request-scoped dependency injection and
SQLAlchemy session lifecycle wiring.
"""

from __future__ import annotations

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
SETTINGS_DOTENV_PATH = PROJECT_ROOT / "infra" / "env" / ".env.dev"


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
        return (
            init_settings,
            DotEnvSettingsSource(
                settings_cls,
                env_file=SETTINGS_DOTENV_PATH,
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
    return Settings()
