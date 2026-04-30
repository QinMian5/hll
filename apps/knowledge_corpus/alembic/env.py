"""
Abstract: Alembic environment setup for knowledge corpus migrations.
Out of scope: Revision authoring and runtime repository behavior.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.schema import CreateSchema

from knowledge_corpus.config import load_migration_settings, load_settings
from knowledge_corpus.db.base import Base
from knowledge_corpus.wikipedia import model as wikipedia_model
from knowledge_corpus.wikipedia.types import WIKIPEDIA_SCHEMA

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = load_migration_settings()
runtime_settings = load_settings()

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url,
)

target_metadata = Base.metadata
REGISTERED_MODEL_MODULES = (wikipedia_model,)
REGISTERED_SCHEMAS = (WIKIPEDIA_SCHEMA,)


def _quote_ident(identifier: str) -> str:
    return identifier.replace('"', '""')


def _grant_schema_privileges(*, connection: Connection, schema_name: str) -> None:
    app_username = make_url(runtime_settings.database_url).username
    migration_username = make_url(settings.database_url).username
    if app_username is None or migration_username is None:
        raise ValueError("Both knowledge corpus database URLs must include usernames.")

    quoted_schema = _quote_ident(schema_name)
    quoted_app_user = _quote_ident(app_username)
    quoted_migration_user = _quote_ident(migration_username)

    connection.execute(text(f'GRANT USAGE ON SCHEMA "{quoted_schema}" TO "{quoted_app_user}"'))
    connection.execute(
        text(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{quoted_migration_user}" '
            f'IN SCHEMA "{quoted_schema}" '
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{quoted_app_user}"'
        )
    )
    connection.execute(
        text(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{quoted_migration_user}" '
            f'IN SCHEMA "{quoted_schema}" '
            f'GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO "{quoted_app_user}"'
        )
    )


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
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
        bootstrap_transaction = connection.begin()
        for schema_name in REGISTERED_SCHEMAS:
            connection.execute(CreateSchema(schema_name, if_not_exists=True))
            _grant_schema_privileges(connection=connection, schema_name=schema_name)
        bootstrap_transaction.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
