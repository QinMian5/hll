"""
Abstract: Unit tests for the source-pipeline persistence projection.
Out of scope: Migration execution and runtime orchestration behavior.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Table

from source_pipeline.db.models import CardReviewJob, WorkflowRun, WorkflowUnit


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


def test_card_review_job_projection_uses_integer_pk_and_handoff_flag() -> None:
    table = cast(Table, CardReviewJob.__table__)

    assert list(table.c.keys()) == [
        "id",
        "workflow_unit_id",
        "ordinal",
        "job_queue_job_id",
        "handoff_done",
        "created_at",
    ]
