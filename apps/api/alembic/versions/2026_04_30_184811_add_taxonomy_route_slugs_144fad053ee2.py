"""
Abstract: Add persisted taxonomy route slugs for canonical Graph View paths.
Out of scope: Taxonomy path-resolution service behavior and frontend routing.

add taxonomy route slugs

Revision ID: 144fad053ee2
Revises: e11cee17761d
Create Date: 2026-04-30 18:48:11.107077

"""

from collections.abc import Sequence

import pgvector  # noqa: F401
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "144fad053ee2"
down_revision: str | Sequence[str] | None = "e11cee17761d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("taxonomy_nodes", sa.Column("route_slug", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE taxonomy_nodes
        SET route_slug = trim(
            both '-' from regexp_replace(lower(trim(name)), '[^a-z0-9]+', '-', 'g')
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM taxonomy_nodes
                WHERE route_slug IS NULL OR route_slug = ''
            ) THEN
                RAISE EXCEPTION
                    'taxonomy_nodes.route_slug backfill produced empty route slugs';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM (
                    SELECT parent_id, route_slug
                    FROM taxonomy_nodes
                    GROUP BY parent_id, route_slug
                    HAVING count(*) > 1
                ) AS route_slug_collisions
            ) THEN
                RAISE EXCEPTION
                    'taxonomy_nodes.route_slug backfill produced sibling route slug collisions';
            END IF;
        END
        $$;
        """
    )
    op.alter_column(
        "taxonomy_nodes",
        "route_slug",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.create_check_constraint(
        op.f("ck_taxonomy_nodes_route_slug_non_empty"),
        "taxonomy_nodes",
        "route_slug <> ''",
    )
    op.create_unique_constraint(
        op.f("uq_taxonomy_nodes_parent_route_slug"),
        "taxonomy_nodes",
        ["parent_id", "route_slug"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("uq_taxonomy_nodes_parent_route_slug"),
        "taxonomy_nodes",
        type_="unique",
    )
    op.drop_constraint(
        op.f("ck_taxonomy_nodes_route_slug_non_empty"),
        "taxonomy_nodes",
        type_="check",
    )
    op.drop_column("taxonomy_nodes", "route_slug")
