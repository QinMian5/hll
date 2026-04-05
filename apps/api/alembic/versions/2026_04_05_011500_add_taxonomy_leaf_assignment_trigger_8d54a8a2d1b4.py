"""add_taxonomy_leaf_assignment_trigger

Revision ID: 8d54a8a2d1b4
Revises: 3e727ac5766a
Create Date: 2026-04-05 01:15:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d54a8a2d1b4"
down_revision: str | Sequence[str] | None = "3e727ac5766a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FUNCTION_NAME = "enforce_node_taxonomy_assignment_leaf"
_TRIGGER_NAME = "trg_node_taxonomy_assignments_leaf_only"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        f"""
        CREATE FUNCTION {_FUNCTION_NAME}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM taxonomy_nodes
                WHERE id = NEW.taxonomy_node_id
                  AND is_leaf = TRUE
            ) THEN
                RAISE EXCEPTION
                    USING ERRCODE = '23514',
                          MESSAGE = (
                              'node_taxonomy_assignments.taxonomy_node_id '
                              'must reference a leaf taxonomy node'
                          );
            END IF;

            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER_NAME}
        BEFORE INSERT OR UPDATE OF taxonomy_node_id
        ON node_taxonomy_assignments
        FOR EACH ROW
        EXECUTE FUNCTION {_FUNCTION_NAME}();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        f"""
        DROP TRIGGER IF EXISTS {_TRIGGER_NAME}
        ON node_taxonomy_assignments;
        """
    )
    op.execute(f"DROP FUNCTION IF EXISTS {_FUNCTION_NAME}();")
