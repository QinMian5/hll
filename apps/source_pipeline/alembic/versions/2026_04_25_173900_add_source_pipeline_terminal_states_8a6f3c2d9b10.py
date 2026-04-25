"""
Abstract: Alembic migration adding terminal queue-state checkpoints for source-pipeline jobs.
Out of scope: Queue worker execution and runtime retry policy.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8a6f3c2d9b10"
down_revision: str | Sequence[str] | None = "5f0c4c7f1e2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workflow_units",
        sa.Column("page_to_card_terminal_state", sa.Text(), nullable=True),
    )
    op.add_column(
        "card_candidates",
        sa.Column("review_terminal_state", sa.Text(), nullable=True),
    )
    op.add_column(
        "card_candidates",
        sa.Column("repair_terminal_state", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("card_candidates", "repair_terminal_state")
    op.drop_column("card_candidates", "review_terminal_state")
    op.drop_column("workflow_units", "page_to_card_terminal_state")
