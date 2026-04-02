"""
Abstract: Alembic environment setup for online and offline migrations.
Out of scope: Migration revision authoring and runtime request handling.
"""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

import modules.knowledge_graph.model  # noqa: F401
from alembic import context
from core.config import load_settings
from shared.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

runtime_args = context.get_x_argument(as_dictionary=True)
env_file_arg = runtime_args.get("env_file")
settings = load_settings(
    env_file=None if env_file_arg is None else Path(env_file_arg).expanduser()
)

config.set_main_option("sqlalchemy.url", settings.migration_database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
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
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
