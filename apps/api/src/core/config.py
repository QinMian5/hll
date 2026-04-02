"""
Abstract: Pydantic settings schema and database URL assembly helpers.
Out of scope: Request-scoped dependency injection and
SQLAlchemy session lifecycle wiring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DOTENV_PATH = PROJECT_ROOT / "infra" / "env" / ".env.dev"


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
        env_file=DEFAULT_DOTENV_PATH,
        env_file_encoding="utf-8",
    )

    db_host: str
    db_port: int
    db_name: str
    app_db_user: str
    app_db_password: str
    migration_db_user: str
    migration_db_password: str
    redis_url: str
    embedding_api_url: str
    embedding_model: str
    embedding_api_key: str
    embedding_timeout_seconds: float = Field(gt=0)
    search_max_matched: int = Field(ge=1)
    search_max_connected: int = Field(ge=1)
    edge_similarity_top_k: int = Field(ge=1)
    edge_similarity_min_strength: float = Field(ge=0.0, le=1.0)

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


def load_settings(*, env_file: Path | str | None = None) -> Settings:
    resolved_env_file = (
        DEFAULT_DOTENV_PATH if env_file is None else Path(env_file).expanduser()
    )
    settings_factory = cast(Any, Settings)
    return cast(Settings, settings_factory(_env_file=resolved_env_file))
