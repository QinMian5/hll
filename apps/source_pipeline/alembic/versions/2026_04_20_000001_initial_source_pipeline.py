"""initial_source_pipeline

Revision ID: 79ff95e15765
Revises:
Create Date: 2026-04-20 22:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "79ff95e15765"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("config_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_runs")),
    )
    op.create_table(
        "workflow_units",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("workflow_run_id", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("page_to_card_job_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.id"],
            name=op.f("fk_workflow_units_workflow_run_id_workflow_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_units")),
    )
    op.create_table(
        "card_review_jobs",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("workflow_unit_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("job_queue_job_id", sa.Integer(), nullable=True),
        sa.Column("handoff_done", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workflow_unit_id"],
            ["workflow_units.id"],
            name=op.f("fk_card_review_jobs_workflow_unit_id_workflow_units"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_card_review_jobs")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("card_review_jobs")
    op.drop_table("workflow_units")
    op.drop_table("workflow_runs")
