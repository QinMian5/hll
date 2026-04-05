"""
Abstract: Pydantic settings schema and loaders for runtime and migration
configuration.
Out of scope: Request-scoped dependency injection and SQLAlchemy session
lifecycle wiring.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_API_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    redis_url: str
    embedding_api_url: str
    embedding_model: str
    embedding_api_key: str
    embedding_timeout_seconds: float = Field(gt=0)
    search_max_matched: int = Field(ge=1)
    search_max_connected: int = Field(ge=1)
    edge_similarity_top_k: int = Field(ge=1)
    edge_similarity_min_strength: float = Field(ge=0.0, le=1.0)
    log_level: str = Field(default="INFO", min_length=1)
    log_file_path: str
    log_file_max_bytes: int = Field(default=10_485_760, gt=0)
    log_file_backup_count: int = Field(default=5, ge=1)


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_API_MIGRATION_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str


def load_settings() -> Settings:
    return Settings.model_validate(EnvSettingsSource(Settings)())


def load_migration_settings() -> MigrationSettings:
    return MigrationSettings.model_validate(EnvSettingsSource(MigrationSettings)())
