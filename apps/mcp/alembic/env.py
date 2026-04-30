"""
Abstract: Alembic environment setup for public MCP service migrations.
Out of scope: Runtime MCP request handling and revision authoring.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from knowledge_mcp.analytics import model as analytics_model
from knowledge_mcp.config import load_migration_settings
from knowledge_mcp.db.metadata import metadata
from knowledge_mcp.usage import model as usage_model

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

migration_settings = load_migration_settings()

config.set_main_option("sqlalchemy.url", migration_settings.database_url)

target_metadata = metadata
_registered_models = (analytics_model, usage_model)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_server_default=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
