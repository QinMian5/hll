"""
Abstract: Unit tests for MCP runtime settings parsing.
Out of scope: Container orchestration and live secret provisioning.
"""

from __future__ import annotations

import pytest

from knowledge_mcp.config import (
    Settings,
    load_database_settings,
    load_migration_settings,
    load_settings,
)


def test_settings_accept_space_or_comma_separated_tuple_env_values() -> None:
    settings = Settings.model_validate(
        {
            "public_base_url": "https://knowledge.example.com/mcp",
            "internal_api_base_url": "http://api:8000",
            "redis_url": "redis://redis:6379/0",
            "database_url": "postgresql+psycopg://mcp:secret@mcp_db:5432/knowledge_mcp",
            "logto_issuer": "https://logto.example.com/oidc",
            "logto_discovery_url": "https://logto.example.com/oidc/.well-known/openid-configuration",
            "logto_token_url": "https://logto.example.com/oidc/token",
            "logto_resource": "https://knowledge.example.com/mcp",
            "logto_required_scopes": "search:execute other:scope",
            "logto_token_exchange_client_id": "mcp-token-exchange",
            "logto_token_exchange_client_secret": "secret",
            "pat_fingerprint_secret": "x" * 32,
            "allowed_origins": "https://knowledge.example.com,https://app.example.com",
        }
    )

    assert settings.logto_required_scopes == ("search:execute", "other:scope")
    assert settings.allowed_origins == (
        "https://knowledge.example.com",
        "https://app.example.com",
    )


def test_load_settings_accepts_space_or_comma_separated_env_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "KNOWLEDGE_MCP_PUBLIC_BASE_URL": "https://knowledge.example.com/mcp",
        "KNOWLEDGE_MCP_INTERNAL_API_BASE_URL": "http://api:8000",
        "KNOWLEDGE_MCP_REDIS_URL": "redis://redis:6379/0",
        "KNOWLEDGE_MCP_DATABASE_URL": "postgresql+psycopg://mcp:secret@mcp_db:5432/knowledge_mcp",
        "KNOWLEDGE_MCP_LOGTO_ISSUER": "https://logto.example.com/oidc",
        "KNOWLEDGE_MCP_LOGTO_DISCOVERY_URL": (
            "https://logto.example.com/oidc/.well-known/openid-configuration"
        ),
        "KNOWLEDGE_MCP_LOGTO_TOKEN_URL": "https://logto.example.com/oidc/token",
        "KNOWLEDGE_MCP_LOGTO_RESOURCE": "https://knowledge.example.com/mcp",
        "KNOWLEDGE_MCP_LOGTO_REQUIRED_SCOPES": "search:execute other:scope",
        "KNOWLEDGE_MCP_LOGTO_TOKEN_EXCHANGE_CLIENT_ID": "mcp-token-exchange",
        "KNOWLEDGE_MCP_LOGTO_TOKEN_EXCHANGE_CLIENT_SECRET": "secret",
        "KNOWLEDGE_MCP_PAT_FINGERPRINT_SECRET": "x" * 32,
        "KNOWLEDGE_MCP_ALLOWED_ORIGINS": "https://knowledge.example.com,https://app.example.com",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    settings = load_settings()

    assert settings.logto_required_scopes == ("search:execute", "other:scope")
    assert settings.allowed_origins == (
        "https://knowledge.example.com",
        "https://app.example.com",
    )


def test_database_and_migration_settings_load_minimal_database_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "KNOWLEDGE_MCP_DATABASE_URL",
        "postgresql+psycopg://mcp:secret@mcp_db:5432/knowledge_mcp",
    )
    monkeypatch.setenv(
        "KNOWLEDGE_MCP_MIGRATION_DATABASE_URL",
        "postgresql+psycopg://migration:secret@mcp_db:5432/knowledge_mcp",
    )

    assert load_database_settings().database_url == (
        "postgresql+psycopg://mcp:secret@mcp_db:5432/knowledge_mcp"
    )
    assert load_migration_settings().database_url == (
        "postgresql+psycopg://migration:secret@mcp_db:5432/knowledge_mcp"
    )
