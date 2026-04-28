"""
Abstract: Runtime settings for the public Knowledge MCP service.
Out of scope: Secret provisioning and environment-specific deployment policy.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, EnvSettingsSource, NoDecode, SettingsConfigDict


def _split_csv_or_space(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        normalized = value.replace(",", " ")
        return tuple(part for part in normalized.split() if part)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(part) for part in value if str(part))
    raise TypeError("Expected a string or sequence of strings.")


StringTuple = Annotated[tuple[str, ...], NoDecode, BeforeValidator(_split_csv_or_space)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_MCP_",
        extra="forbid",
        case_sensitive=False,
    )

    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    public_base_url: str
    internal_api_base_url: str
    redis_url: str
    database_url: str

    logto_issuer: str
    logto_discovery_url: str
    logto_token_url: str
    logto_resource: str
    logto_required_scopes: StringTuple = ("search:execute",)
    logto_token_exchange_client_id: str
    logto_token_exchange_client_secret: str

    pat_fingerprint_secret: str = Field(min_length=32)
    allowed_origins: StringTuple = ()
    token_cache_ttl_seconds: int = Field(default=300, ge=1)
    auth_http_timeout_seconds: float = Field(default=5.0, gt=0)
    usage_summary_auth_resource: str
    usage_summary_required_scope: str = "usage:read"
    usage_summary_allowed_client_id: str
    usage_summary_max_batch_size: int = Field(default=100, ge=1)

    quota_redis_prefix: str = "knowledge:mcp:quota:"
    user_burst_limit: int = Field(default=60, ge=1)
    user_burst_window_seconds: int = Field(default=60, ge=1)
    user_total_limit: int = Field(default=1000, ge=1)
    user_total_window_seconds: int = Field(default=86400, ge=1)
    pat_burst_limit: int = Field(default=30, ge=1)
    pat_burst_window_seconds: int = Field(default=60, ge=1)
    pat_total_limit: int = Field(default=500, ge=1)
    pat_total_window_seconds: int = Field(default=86400, ge=1)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_MCP_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_MCP_MIGRATION_",
        extra="forbid",
        case_sensitive=False,
    )

    database_url: str


def load_settings() -> Settings:
    return Settings.model_validate(EnvSettingsSource(Settings)())


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings.model_validate(EnvSettingsSource(DatabaseSettings)())


def load_migration_settings() -> MigrationSettings:
    return MigrationSettings.model_validate(EnvSettingsSource(MigrationSettings)())
