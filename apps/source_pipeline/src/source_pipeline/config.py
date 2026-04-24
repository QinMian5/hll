"""
Abstract: App-local settings contract for the source-pipeline app.
Out of scope: SQLAlchemy engine construction and runtime orchestration behavior.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOURCE_PIPELINE_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str
    job_queue_base_url: str
    job_queue_token_url: str
    job_queue_client_id: str
    job_queue_client_secret: str
    job_queue_resource: str
    job_queue_scopes: str = "jobs:create results:read"
    poll_interval_seconds: float = 5.0
    poll_batch_size: int = 100


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOURCE_PIPELINE_MIGRATION_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str


def load_settings() -> Settings:
    return Settings.model_validate(EnvSettingsSource(Settings)())


def load_migration_settings() -> MigrationSettings:
    return MigrationSettings.model_validate(EnvSettingsSource(MigrationSettings)())
