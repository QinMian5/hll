"""
Abstract: Alembic migration adding a required shared reason to card proposals.
Out of scope: Runtime proposal validation and browser proposal forms.

Revision ID: 2cb79ef5a6d1
Revises: 9c2e5b7d4a10
Create Date: 2026-05-04 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2cb79ef5a6d1"
down_revision: str | Sequence[str] | None = "9c2e5b7d4a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("card_proposals", sa.Column("reason", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE card_proposals
        SET reason = COALESCE(
            NULLIF(BTRIM(payload ->> 'reason'), ''),
            NULLIF(BTRIM(review_note), ''),
            'Legacy proposal imported before reason capture.'
        )
        WHERE reason IS NULL OR BTRIM(reason) = ''
        """
    )
    op.alter_column("card_proposals", "reason", nullable=False)
    op.create_check_constraint(
        op.f("ck_card_proposals_reason_nonempty"),
        "card_proposals",
        "btrim(reason) <> ''",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("ck_card_proposals_reason_nonempty"),
        "card_proposals",
        type_="check",
    )
    op.drop_column("card_proposals", "reason")
