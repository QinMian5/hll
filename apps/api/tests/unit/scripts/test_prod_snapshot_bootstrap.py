"""
Abstract: Unit tests for production snapshot bootstrap table and safety helpers.
Out of scope: Docker execution, pg_dump output, and live database mutation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from entrypoints.ops.prod_snapshot_bootstrap import (
    API_BOOTSTRAP_TABLES,
    assert_development_env_file,
    build_pg_dump_table_args,
    build_truncate_sql,
)


@pytest.mark.unit
def test_api_bootstrap_tables_cover_prod_snapshot_closure() -> None:
    assert API_BOOTSTRAP_TABLES == (
        "ingestion_requests",
        "nodes",
        "taxonomy_classification_webhook_events",
        "taxonomy_nodes",
        "card_versions",
        "edges",
        "node_taxonomy_assignments",
        "taxonomy_classification_jobs",
        "taxonomy_classification_webhook_wakeups",
        "adjacency",
        "card_suggested_edits",
        "taxonomy_leaf_projection_edges",
    )
    assert "alembic_version" not in API_BOOTSTRAP_TABLES
    assert len(set(API_BOOTSTRAP_TABLES)) == len(API_BOOTSTRAP_TABLES)


@pytest.mark.unit
def test_pg_dump_args_scope_every_table_to_public_schema() -> None:
    assert build_pg_dump_table_args() == tuple(
        f"--table=public.{table_name}" for table_name in API_BOOTSTRAP_TABLES
    )


@pytest.mark.unit
def test_truncate_sql_clears_only_bootstrap_tables_and_resets_sequences() -> None:
    truncate_sql = build_truncate_sql()

    assert truncate_sql.startswith("TRUNCATE TABLE\n")
    assert truncate_sql.endswith("\nRESTART IDENTITY CASCADE;\n")
    for table_name in API_BOOTSTRAP_TABLES:
        assert f"public.{table_name}" in truncate_sql
    assert "public.alembic_version" not in truncate_sql


@pytest.mark.unit
def test_dev_import_guard_accepts_only_dev_env_file() -> None:
    assert_development_env_file(Path("infra/env/.env.dev"))

    with pytest.raises(ValueError, match=r"\.env\.dev"):
        assert_development_env_file(Path("infra/env/.env.prod"))
