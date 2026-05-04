"""
Abstract: Add durable taxonomy card-scope layout read models and compute requests.
Out of scope: Runtime layout computation and API transport contracts.
"""

from __future__ import annotations

from collections.abc import Sequence

import pgvector  # noqa: F401
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9c2e5b7d4a10"
down_revision: str | Sequence[str] | None = "77df962193b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "taxonomy_card_scope_layouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_kind", sa.Text(), nullable=False),
        sa.Column("taxonomy_node_id", sa.Integer(), nullable=False),
        sa.Column("layout_version", sa.Text(), nullable=False),
        sa.Column("input_fingerprint", sa.Text(), nullable=False),
        sa.Column("layout_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
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
            "scope_kind IN ('taxonomy_node', 'virtual_unclassified')",
            name=op.f("ck_taxonomy_card_scope_layouts_scope_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_node_id"],
            ["taxonomy_nodes.id"],
            name=op.f("fk_taxonomy_card_scope_layouts_taxonomy_node_id_taxonomy_nodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_taxonomy_card_scope_layouts")),
        sa.UniqueConstraint(
            "scope_kind",
            "taxonomy_node_id",
            "layout_version",
            name=op.f("uq_taxonomy_card_scope_layouts_scope_version"),
        ),
    )
    op.create_index(
        "ix_taxonomy_card_scope_layouts_input_fingerprint",
        "taxonomy_card_scope_layouts",
        ["input_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_taxonomy_card_scope_layouts_scope",
        "taxonomy_card_scope_layouts",
        ["scope_kind", "taxonomy_node_id"],
        unique=False,
    )
    op.create_table(
        "taxonomy_card_scope_layout_compute_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_kind", sa.Text(), nullable=False),
        sa.Column("taxonomy_node_id", sa.Integer(), nullable=False),
        sa.Column("layout_version", sa.Text(), nullable=False),
        sa.Column("input_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
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
            "scope_kind IN ('taxonomy_node', 'virtual_unclassified')",
            name=op.f("ck_taxonomy_card_scope_layout_compute_requests_scope_kind"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name=op.f("ck_taxonomy_card_scope_layout_compute_requests_status"),
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=op.f("ck_taxonomy_card_scope_layout_compute_requests_attempt_count"),
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_node_id"],
            ["taxonomy_nodes.id"],
            name=op.f(
                "fk_taxonomy_card_scope_layout_compute_requests_taxonomy_node_id_taxonomy_nodes"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_taxonomy_card_scope_layout_compute_requests"),
        ),
        sa.UniqueConstraint(
            "scope_kind",
            "taxonomy_node_id",
            "layout_version",
            name=op.f("uq_taxonomy_card_scope_layout_compute_requests_scope_version"),
        ),
    )
    op.create_index(
        "ix_taxonomy_card_scope_layout_compute_requests_scope",
        "taxonomy_card_scope_layout_compute_requests",
        ["scope_kind", "taxonomy_node_id"],
        unique=False,
    )
    op.create_index(
        "ix_taxonomy_card_scope_layout_compute_requests_status_requested",
        "taxonomy_card_scope_layout_compute_requests",
        ["status", "requested_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_taxonomy_card_scope_layout_compute_requests_status_requested",
        table_name="taxonomy_card_scope_layout_compute_requests",
    )
    op.drop_index(
        "ix_taxonomy_card_scope_layout_compute_requests_scope",
        table_name="taxonomy_card_scope_layout_compute_requests",
    )
    op.drop_table("taxonomy_card_scope_layout_compute_requests")
    op.drop_index(
        "ix_taxonomy_card_scope_layouts_scope",
        table_name="taxonomy_card_scope_layouts",
    )
    op.drop_index(
        "ix_taxonomy_card_scope_layouts_input_fingerprint",
        table_name="taxonomy_card_scope_layouts",
    )
    op.drop_table("taxonomy_card_scope_layouts")
