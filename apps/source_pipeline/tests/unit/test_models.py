"""
Abstract: Unit tests for the source-pipeline persistence projection.
Out of scope: Migration execution and runtime orchestration behavior.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Table

from source_pipeline.db.models import CardCandidate, WorkflowRun, WorkflowUnit


def test_workflow_run_projection_contains_expected_columns() -> None:
    table = cast(Table, WorkflowRun.__table__)

    assert list(table.c.keys()) == [
        "id",
        "source_kind",
        "config_payload",
        "created_at",
    ]


def test_workflow_unit_projection_stores_only_minimal_linkage_state() -> None:
    table = cast(Table, WorkflowUnit.__table__)

    assert list(table.c.keys()) == [
        "id",
        "workflow_run_id",
        "source_kind",
        "source_ref",
        "payload",
        "page_to_card_job_id",
        "created_at",
    ]


def test_card_candidate_projection_stores_candidate_lineage_and_job_links() -> None:
    table = cast(Table, CardCandidate.__table__)

    assert list(table.c.keys()) == [
        "id",
        "workflow_unit_id",
        "parent_candidate_id",
        "card_payload",
        "origin_step",
        "origin_job_id",
        "origin_ordinal",
        "review_job_id",
        "repair_job_id",
        "ingestion_handoff_done",
        "created_at",
    ]


def test_card_candidate_projection_has_idempotency_constraints() -> None:
    table = cast(Table, CardCandidate.__table__)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "uq_card_candidates_workflow_origin" in constraint_names
    assert "uq_card_candidates_parent_origin" in constraint_names
