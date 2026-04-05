"""
Abstract: App-local settings contract for the isolated knowledge corpus app.
Out of scope: SQLAlchemy engine construction and migration environment wiring.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_CORPUS_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_CORPUS_MIGRATION_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str


def load_settings() -> Settings:
    return Settings.model_validate(EnvSettingsSource(Settings)())


def load_migration_settings() -> MigrationSettings:
    return MigrationSettings.model_validate(EnvSettingsSource(MigrationSettings)())
