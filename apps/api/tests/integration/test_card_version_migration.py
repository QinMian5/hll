"""
Abstract: Integration checks for card-version schema convergence on migrated databases.
Out of scope: Alembic command-line invocation and suggestion review behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from core.config import load_migration_settings

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.migration, pytest.mark.anyio]

API_DIR = Path(__file__).resolve().parents[2]
PRE_CARD_VERSION_REVISION = "040e04067f03"


async def test_card_version_tables_and_constraints_exist_after_migration(
    db_session: AsyncSession,
) -> None:
    table_rows = (
        await db_session.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename IN ('card_versions', 'card_suggested_edits')
                ORDER BY tablename
                """
            )
        )
    ).scalars()
    constraint_rows = (
        await db_session.execute(
            text(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conname IN (
                    'ck_nodes_current_version_positive',
                    'ck_card_versions_version_positive',
                    'uq_card_versions_node_version',
                    'fk_card_suggested_edits_base_version',
                    'ck_card_suggested_edits_base_version_positive',
                    'ck_card_suggested_edits_status'
                )
                ORDER BY conname
                """
            )
        )
    ).scalars()

    assert set(table_rows.all()) == {"card_versions", "card_suggested_edits"}
    assert set(constraint_rows.all()) == {
        "ck_nodes_current_version_positive",
        "ck_card_versions_version_positive",
        "uq_card_versions_node_version",
        "fk_card_suggested_edits_base_version",
        "ck_card_suggested_edits_base_version_positive",
        "ck_card_suggested_edits_status",
    }


def test_card_version_migration_backfills_existing_nodes() -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    migration_url = load_migration_settings().database_url
    engine = create_engine(migration_url)
    node_id: int | None = None
    embedding = "[" + ",".join("0" for _ in range(1536)) + "]"

    try:
        command.downgrade(config, PRE_CARD_VERSION_REVISION)
        with engine.begin() as connection:
            node_id = connection.execute(
                text(
                    """
                    INSERT INTO nodes (title, content, embedding)
                    VALUES (:title, :content, CAST(:embedding AS vector))
                    RETURNING id
                    """
                ),
                {
                    "content": "Pre-migration content",
                    "embedding": embedding,
                    "title": "Pre-migration title",
                },
            ).scalar_one()

        command.upgrade(config, "head")

        with engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT nodes.current_version, card_versions.version,
                           card_versions.title, card_versions.content
                    FROM nodes
                    JOIN card_versions ON card_versions.node_id = nodes.id
                    WHERE nodes.id = :node_id
                    """
                ),
                {"node_id": node_id},
            ).one()

            assert row.current_version == 1
            assert row.version == 1
            assert row.title == "Pre-migration title"
            assert row.content == "Pre-migration content"
    finally:
        command.upgrade(config, "head")
        if node_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM nodes WHERE id = :node_id"), {"node_id": node_id}
                )
        engine.dispose()
