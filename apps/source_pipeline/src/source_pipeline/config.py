"""
Abstract: App-local settings contract for the source-pipeline app.
Out of scope: SQLAlchemy engine construction and runtime orchestration behavior.
"""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOURCE_PIPELINE_",
        extra="forbid",
        case_sensitive=False,
    )

    role: Literal["orchestrator", "webhook_receiver"] = "orchestrator"
    database_url: str
    knowledge_api_base_url: str | None = None
    job_queue_base_url: str | None = None
    job_queue_token_url: str | None = None
    job_queue_client_id: str | None = None
    job_queue_client_secret: str | None = None
    job_queue_resource: str | None = None
    job_queue_scopes: str = "jobs:create results:read"
    webhook_auth_issuer: str | None = None
    webhook_auth_resource: str | None = None
    webhook_auth_discovery_url: str | None = None
    webhook_allowed_client_id: str | None = None
    webhook_auth_http_timeout_seconds: float = 5.0
    webhook_public_path: str = "/source-pipeline/webhooks/job-queue"
    poll_interval_seconds: float = 5.0
    poll_batch_size: int = 100
    reconcile_interval_seconds: float = 3600
    reconcile_batch_size: int = 100

    @model_validator(mode="after")
    def validate_role_specific_settings(self) -> Settings:
        if self.role == "orchestrator":
            missing = [
                name
                for name, value in {
                    "knowledge_api_base_url": self.knowledge_api_base_url,
                    "job_queue_base_url": self.job_queue_base_url,
                    "job_queue_token_url": self.job_queue_token_url,
                    "job_queue_client_id": self.job_queue_client_id,
                    "job_queue_client_secret": self.job_queue_client_secret,
                    "job_queue_resource": self.job_queue_resource,
                }.items()
                if value in (None, "")
            ]
            if missing:
                raise ValueError(
                    "orchestrator settings are required: " + ", ".join(sorted(missing))
                )
        if self.role == "webhook_receiver":
            missing = [
                name
                for name, value in {
                    "webhook_auth_issuer": self.webhook_auth_issuer,
                    "webhook_auth_resource": self.webhook_auth_resource,
                    "webhook_auth_discovery_url": self.webhook_auth_discovery_url,
                    "webhook_allowed_client_id": self.webhook_allowed_client_id,
                }.items()
                if value in (None, "")
            ]
            if missing:
                raise ValueError(
                    "webhook receiver settings are required: " + ", ".join(sorted(missing))
                )
        return self


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
