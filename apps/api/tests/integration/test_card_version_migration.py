"""
Abstract: Integration checks for card-version schema convergence on migrated databases.
Out of scope: Alembic command-line invocation and suggestion review behavior.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.migration, pytest.mark.anyio]


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
                  AND tablename IN (
                    'card_versions',
                    'workspace_roles',
                    'card_proposals',
                    'proposal_apply_audits'
                  )
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
                    'ck_nodes_lifecycle_state',
                    'ck_card_versions_version_positive',
                    'uq_card_versions_node_version',
                    'ck_workspace_roles_role',
                    'ck_card_proposals_proposal_type',
                    'ck_card_proposals_status',
                    'ck_card_proposals_reason_nonempty',
                    'fk_proposal_apply_audits_proposal_id_card_proposals'
                )
                ORDER BY conname
                """
            )
        )
    ).scalars()

    assert set(table_rows.all()) == {
        "card_versions",
        "workspace_roles",
        "card_proposals",
        "proposal_apply_audits",
    }
    assert set(constraint_rows.all()) == {
        "ck_nodes_current_version_positive",
        "ck_nodes_lifecycle_state",
        "ck_card_versions_version_positive",
        "uq_card_versions_node_version",
        "ck_workspace_roles_role",
        "ck_card_proposals_proposal_type",
        "ck_card_proposals_status",
        "ck_card_proposals_reason_nonempty",
        "fk_proposal_apply_audits_proposal_id_card_proposals",
    }


async def test_card_versions_can_reference_current_baseline_nodes(
    db_session: AsyncSession,
) -> None:
    embedding = "[" + ",".join("0" for _ in range(1536)) + "]"
    node_id = (
        await db_session.execute(
            text(
                """
                INSERT INTO nodes (title, content, embedding)
                VALUES (:title, :content, CAST(:embedding AS vector))
                RETURNING id
                """
            ),
            {
                "content": "Baseline content",
                "embedding": embedding,
                "title": "Baseline title",
            },
        )
    ).scalar_one()
    await db_session.execute(
        text(
            """
            INSERT INTO card_versions (node_id, version, title, content)
            VALUES (:node_id, 1, :title, :content)
            """
        ),
        {
            "content": "Baseline content",
            "node_id": node_id,
            "title": "Baseline title",
        },
    )

    row = (
        await db_session.execute(
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
        )
    ).one()

    assert row.current_version == 1
    assert row.version == 1
    assert row.title == "Baseline title"
    assert row.content == "Baseline content"
