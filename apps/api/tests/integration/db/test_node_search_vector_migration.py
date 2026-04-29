"""
Abstract: Integration checks for node full-text search projection on migrated databases.
Out of scope: Search ranking policy and HTTP route behavior.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from core.config import load_migration_settings

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.migration]


def test_nodes_search_vector_baseline_generates_values_and_index() -> None:
    migration_url = load_migration_settings().database_url
    engine = create_engine(migration_url)
    node_id: int | None = None
    embedding = "[" + ",".join("0" for _ in range(1536)) + "]"

    try:
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
        if node_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM nodes WHERE id = :node_id"), {"node_id": node_id}
                )
        engine.dispose()
