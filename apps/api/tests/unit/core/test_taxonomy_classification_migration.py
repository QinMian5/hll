"""
Abstract: Unit checks for the taxonomy-classification migration boundary.
Out of scope: Alembic execution and database engine behavior.
"""

from __future__ import annotations

from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "2026_04_26_180000_add_taxonomy_classification_queue_tables_f8a9b0c1d2e3.py"
)


def test_taxonomy_classification_migration_does_not_backfill_business_data() -> None:
    migration_source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "op.execute(" not in migration_source
    assert "DO $$" not in migration_source
    assert "INSERT INTO taxonomy_nodes" not in migration_source
    assert "UPDATE node_taxonomy_assignments" not in migration_source
