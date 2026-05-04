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

REPO_ROOT = Path(__file__).resolve().parents[5]
DEV_UP_SCRIPT = REPO_ROOT / "scripts" / "dev-up.sh"
DEV_BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts" / "bootstrap-dev-api-from-prod-snapshot.sh"
DEV_BOOTSTRAP_SNAPSHOT = REPO_ROOT / "apps" / "api" / "bootstrap" / "prod-api-bootstrap.sql"


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
        "taxonomy_classification_continuation_requests",
        "taxonomy_classification_webhook_wakeups",
        "adjacency",
        "workspace_roles",
        "card_proposals",
        "proposal_apply_audits",
        "taxonomy_scope_projection_edges",
        "taxonomy_card_scope_layouts",
    )
    assert "alembic_version" not in API_BOOTSTRAP_TABLES
    assert "taxonomy_card_scope_layout_compute_requests" not in API_BOOTSTRAP_TABLES
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


@pytest.mark.unit
def test_dev_bootstrap_stops_api_database_and_layout_runtimes_before_restore() -> None:
    script = DEV_BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")
    stop_index = script.index('docker compose "${compose_args[@]}" stop')
    restore_index = script.index('} | docker compose "${compose_args[@]}" exec -T postgres')
    stop_block = script[stop_index:restore_index]

    for service_name in (
        "api",
        "worker",
        "taxonomy_view_layout_runtime",
        "taxonomy_classification_runtime",
        "taxonomy_classification_webhook_receiver",
    ):
        assert service_name in stop_block


@pytest.mark.unit
def test_dev_bootstrap_flushes_redis_after_snapshot_restore() -> None:
    script = DEV_BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")
    restore_index = script.index('} | docker compose "${compose_args[@]}" exec -T postgres')
    redis_flush_index = script.index("redis-cli FLUSHDB")

    assert restore_index < redis_flush_index


@pytest.mark.unit
def test_dev_up_restores_snapshot_before_starting_stack() -> None:
    script = DEV_UP_SCRIPT.read_text(encoding="utf-8")
    restore_index = script.index("scripts/bootstrap-dev-api-from-prod-snapshot.sh")
    start_index = script.index('docker compose "${compose_args[@]}" up -d --build')

    assert restore_index < start_index


@pytest.mark.unit
def test_committed_dev_bootstrap_snapshot_matches_current_taxonomy_schema() -> None:
    snapshot = DEV_BOOTSTRAP_SNAPSHOT.read_text(encoding="utf-8")
    taxonomy_node_inserts = [
        line
        for line in snapshot.splitlines()
        if line.startswith("INSERT INTO public.taxonomy_nodes")
    ]

    assert "is_leaf" not in snapshot
    assert "source_unclassified_node_id" not in snapshot
    assert "taxonomy_leaf_projection_edges" not in snapshot
    assert taxonomy_node_inserts
    for line in taxonomy_node_inserts:
        assert line.startswith(
            "INSERT INTO public.taxonomy_nodes (id, parent_id, name, route_slug, depth)"
        )
        assert "'Unclassified'" not in line


@pytest.mark.unit
def test_committed_dev_bootstrap_snapshot_places_cards_under_science() -> None:
    snapshot = DEV_BOOTSTRAP_SNAPSHOT.read_text(encoding="utf-8")
    assignment_inserts = [
        line
        for line in snapshot.splitlines()
        if line.startswith("INSERT INTO public.node_taxonomy_assignments")
    ]

    assert (
        "INSERT INTO public.taxonomy_nodes (id, parent_id, name, route_slug, depth) "
        "VALUES (3, 1, 'Science', 'science', 1);"
    ) in snapshot
    assert len(assignment_inserts) == 56
    assert all(", 3, " in line for line in assignment_inserts)
    assert "INSERT INTO public.taxonomy_scope_projection_edges" in snapshot
    assert "SELECT 'taxonomy_node', 3, id\nFROM public.edges;" in snapshot
