"""
Abstract: App-local settings contract for the isolated knowledge corpus app.
Out of scope: SQLAlchemy engine construction and migration environment wiring.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid",
        case_sensitive=False,
    )

    knowledge_corpus_database_url: str


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid",
        case_sensitive=False,
    )

    knowledge_corpus_migration_database_url: str


def load_settings() -> Settings:
    return Settings.model_validate(EnvSettingsSource(Settings)())


def load_migration_settings() -> MigrationSettings:
    return MigrationSettings.model_validate(EnvSettingsSource(MigrationSettings)())
