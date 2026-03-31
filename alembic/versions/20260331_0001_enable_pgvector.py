"""
Abstract: Enable pgvector extension for the knowledge database.
Out of scope: Table creation and non-extension schema changes.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260331_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Intentional no-op: extension removal is deferred from rollback policy.
    pass

