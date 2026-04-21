"""
Abstract: App-local settings contract for the source-pipeline app.
Out of scope: SQLAlchemy engine construction and runtime orchestration behavior.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class SourcePipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOURCE_PIPELINE_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str
    job_queue_base_url: str
    producer_token: str
    results_reader_token: str
    poll_interval_seconds: float = 5.0
    poll_batch_size: int = 100


class SourcePipelineMigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOURCE_PIPELINE_MIGRATION_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str


def load_settings() -> SourcePipelineSettings:
    return SourcePipelineSettings.model_validate(EnvSettingsSource(SourcePipelineSettings)())


def load_migration_settings() -> SourcePipelineMigrationSettings:
    return SourcePipelineMigrationSettings.model_validate(
        EnvSettingsSource(SourcePipelineMigrationSettings)()
    )
