"""
Abstract: Alembic environment setup for online and offline migrations.
Out of scope: Migration revision authoring and runtime request handling.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from core.config import load_migration_settings
from modules.knowledge_graph import model as knowledge_graph_model
from modules.semantic_map.persistence import model as semantic_map_model
from modules.taxonomy import model as taxonomy_model
from shared.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = load_migration_settings()

config.set_main_option("sqlalchemy.url", settings.migration_database_url)

target_metadata = Base.metadata
REGISTERED_MODEL_MODULES = (knowledge_graph_model, semantic_map_model, taxonomy_model)


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
