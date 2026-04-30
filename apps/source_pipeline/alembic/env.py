"""
Abstract: Alembic environment setup for source-pipeline migrations.
Out of scope: Revision authoring and runtime orchestration behavior.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from source_pipeline.config import load_migration_settings
from source_pipeline.db import models as db_models
from source_pipeline.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

migration_settings = load_migration_settings()

config.set_main_option(
    "sqlalchemy.url",
    migration_settings.database_url,
)

target_metadata = Base.metadata
REGISTERED_MODEL_MODULES = (db_models,)


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
