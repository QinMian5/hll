"""restore missing taxonomy classification revision stamp

Revision ID: 040e04067f03
Revises: f8a9b0c1d2e3
Create Date: 2026-04-27 20:50:11.157871

"""

from collections.abc import Sequence

import pgvector  # noqa: F401
import sqlalchemy as sa  # noqa: F401

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "040e04067f03"
down_revision: str | Sequence[str] | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Compatibility-only revision. The schema changes are owned by f8a9b0c1d2e3.


def downgrade() -> None:
    """Downgrade schema."""
    # Keep rollback metadata-only for the same reason.
