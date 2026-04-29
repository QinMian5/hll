"""
Abstract: Integration checks for node full-text search projection on migrated databases.
Out of scope: Search ranking policy and HTTP route behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from core.config import load_migration_settings

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.migration]

API_DIR = Path(__file__).resolve().parents[3]
PRE_NODE_SEARCH_VECTOR_REVISION = "a1b2c3d4e5f6"


def test_node_search_vector_migration_populates_existing_nodes_and_index() -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    migration_url = load_migration_settings().database_url
    engine = create_engine(migration_url)
    node_id: int | None = None
    embedding = "[" + ",".join("0" for _ in range(1536)) + "]"

    try:
        command.downgrade(config, PRE_NODE_SEARCH_VECTOR_REVISION)
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
                    "content": "Balanced retrieval combines semantic and keyword signals.",
                    "embedding": embedding,
                    "title": "Hybrid Search",
                },
            ).scalar_one()

        command.upgrade(config, "head")

        with engine.begin() as connection:
            search_vector_text = connection.execute(
                text(
                    """
                    SELECT search_vector::text
                    FROM nodes
                    WHERE id = :node_id
                    """
                ),
                {"node_id": node_id},
            ).scalar_one()
            index_definition = connection.execute(
                text(
                    """
                    SELECT indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'nodes'
                      AND indexname = 'ix_nodes_search_vector'
                    """
                )
            ).scalar_one()

            assert "'hybrid'" in search_vector_text
            assert "'retriev'" in search_vector_text
            assert "USING gin" in index_definition
    finally:
        command.upgrade(config, "head")
        if node_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM nodes WHERE id = :node_id"), {"node_id": node_id}
                )
        engine.dispose()
