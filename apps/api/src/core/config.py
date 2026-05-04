"""
Abstract: Pydantic settings schema and loaders for runtime and migration
configuration.
Out of scope: Request-scoped dependency injection and SQLAlchemy session
lifecycle wiring.
"""

from __future__ import annotations

from typing import Self

from pydantic import Field, model_validator
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
    search_response_cache_ttl_seconds: int = Field(ge=1)
    search_embedding_cache_ttl_seconds: int = Field(ge=1)
    taxonomy_view_cache_ttl_seconds: int = Field(ge=1)
    edge_title_mention_top_k: int = Field(ge=0)
    edge_semantic_top_k: int = Field(ge=0)
    edge_semantic_min_strength: float = Field(ge=0.0, le=1.0)
    edge_semantic_candidate_limit: int = Field(ge=0)
    log_level: str = Field(min_length=1)
    log_file_path: str
    log_file_max_bytes: int = Field(gt=0)
    log_file_backup_count: int = Field(ge=1)
    taxonomy_classification_cursor_command: str = Field(min_length=1)
    taxonomy_classification_cursor_workspace_root: str = Field(min_length=1)
    taxonomy_classification_cursor_timeout_seconds: float = Field(gt=0)
    taxonomy_classification_cursor_max_retries: int = Field(ge=1)
    taxonomy_classification_max_workers: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_edge_initialization_settings(self) -> Self:
        if self.edge_semantic_candidate_limit < self.edge_semantic_top_k:
            raise ValueError(
                "edge_semantic_candidate_limit must be greater than or equal to "
                "edge_semantic_top_k."
            )
        return self


class MigrationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_API_MIGRATION_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str


def load_settings() -> Settings:
    return Settings.model_validate(EnvSettingsSource(Settings)())


class TaxonomyClassificationRuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_API_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    taxonomy_classification_queue_name: str = Field(
        min_length=1,
    )
    taxonomy_classification_job_queue_base_url: str = Field(min_length=1)
    taxonomy_classification_job_queue_token_url: str = Field(min_length=1)
    taxonomy_classification_job_queue_client_id: str = Field(min_length=1)
    taxonomy_classification_job_queue_client_secret: str = Field(min_length=1)
    taxonomy_classification_job_queue_resource: str = Field(min_length=1)
    taxonomy_classification_job_queue_scopes: str = Field(min_length=1)
    taxonomy_classification_poll_interval_seconds: float = Field(gt=0)
    taxonomy_classification_poll_batch_size: int = Field(ge=1)
    taxonomy_classification_reconcile_interval_seconds: float = Field(gt=0)
    taxonomy_classification_reconcile_batch_size: int = Field(ge=1)
    taxonomy_classification_continuation_request_batch_size: int = Field(ge=1, le=1000)
    taxonomy_classification_continuation_flush_interval_seconds: float = Field(gt=0)
    taxonomy_classification_projection_refresh_batch_size: int = Field(ge=1)


class TaxonomyViewLayoutRuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_API_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    redis_url: str
    taxonomy_view_cache_ttl_seconds: int = Field(ge=1)
    edge_title_mention_top_k: int = Field(ge=0)
    edge_semantic_top_k: int = Field(ge=0)
    edge_semantic_min_strength: float = Field(ge=0.0, le=1.0)
    edge_semantic_candidate_limit: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_edge_initialization_settings(self) -> Self:
        if self.edge_semantic_candidate_limit < self.edge_semantic_top_k:
            raise ValueError(
                "edge_semantic_candidate_limit must be greater than or equal to "
                "edge_semantic_top_k."
            )
        return self


class TaxonomyClassificationWebhookReceiverSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_API_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    taxonomy_classification_queue_name: str = Field(
        min_length=1,
    )
    taxonomy_classification_webhook_auth_issuer: str = Field(min_length=1)
    taxonomy_classification_webhook_auth_resource: str = Field(min_length=1)
    taxonomy_classification_webhook_auth_discovery_url: str = Field(min_length=1)
    taxonomy_classification_webhook_allowed_client_id: str = Field(min_length=1)
    taxonomy_classification_webhook_auth_http_timeout_seconds: float = Field(gt=0)
    taxonomy_classification_webhook_public_path: str = Field(
        min_length=1,
    )


def load_taxonomy_classification_runtime_settings() -> TaxonomyClassificationRuntimeSettings:
    return TaxonomyClassificationRuntimeSettings.model_validate(
        EnvSettingsSource(TaxonomyClassificationRuntimeSettings)()
    )


def load_taxonomy_view_layout_runtime_settings() -> TaxonomyViewLayoutRuntimeSettings:
    return TaxonomyViewLayoutRuntimeSettings.model_validate(
        EnvSettingsSource(TaxonomyViewLayoutRuntimeSettings)()
    )


def load_taxonomy_classification_webhook_receiver_settings() -> (
    TaxonomyClassificationWebhookReceiverSettings
):
    return TaxonomyClassificationWebhookReceiverSettings.model_validate(
        EnvSettingsSource(TaxonomyClassificationWebhookReceiverSettings)()
    )


def load_migration_settings() -> MigrationSettings:
    return MigrationSettings.model_validate(EnvSettingsSource(MigrationSettings)())
