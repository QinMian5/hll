"""add card versions and suggested edits

Revision ID: a1b2c3d4e5f6
Revises: 040e04067f03
Create Date: 2026-04-28 18:00:00.000000

"""

from collections.abc import Sequence

import pgvector  # noqa: F401
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "040e04067f03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "nodes",
        sa.Column(
            "current_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_nodes_current_version_positive"),
        "nodes",
        "current_version >= 1",
    )
    op.create_table(
        "card_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_card_versions_version_positive")),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["nodes.id"],
            name=op.f("fk_card_versions_node_id_nodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_card_versions")),
        sa.UniqueConstraint("node_id", "version", name="uq_card_versions_node_version"),
    )
    op.create_index("ix_card_versions_node_id", "card_versions", ["node_id"], unique=False)
    op.execute(
        sa.text(
            """
            INSERT INTO card_versions (node_id, version, title, content)
            SELECT id, current_version, title, content
            FROM nodes
            """
        )
    )
    op.create_table(
        "card_suggested_edits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("suggested_title", sa.Text(), nullable=False),
        sa.Column("suggested_content", sa.Text(), nullable=False),
        sa.Column("suggested_by_user_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "base_version >= 1",
            name=op.f("ck_card_suggested_edits_base_version_positive"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name=op.f("ck_card_suggested_edits_status"),
        ),
        sa.ForeignKeyConstraint(
            ["node_id", "base_version"],
            ["card_versions.node_id", "card_versions.version"],
            name="fk_card_suggested_edits_base_version",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_card_suggested_edits")),
    )
    op.create_index(
        "ix_card_suggested_edits_node_id",
        "card_suggested_edits",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        "ix_card_suggested_edits_status",
        "card_suggested_edits",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_card_suggested_edits_suggested_by_user_id",
        "card_suggested_edits",
        ["suggested_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_card_suggested_edits_suggested_by_user_id", table_name="card_suggested_edits")
    op.drop_index("ix_card_suggested_edits_status", table_name="card_suggested_edits")
    op.drop_index("ix_card_suggested_edits_node_id", table_name="card_suggested_edits")
    op.drop_table("card_suggested_edits")
    op.drop_index("ix_card_versions_node_id", table_name="card_versions")
    op.drop_table("card_versions")
    op.drop_constraint(op.f("ck_nodes_current_version_positive"), "nodes", type_="check")
    op.drop_column("nodes", "current_version")
