"""enable_pgvector

Revision ID: 2a855fefebad
Revises:
Create Date: 2026-03-31 20:45:43.541978

"""

from collections.abc import Sequence

import pgvector  # noqa: F401
import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "2a855fefebad"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Downgrade schema."""
    # no-op by design: extension remains installed across downgrades
    pass
