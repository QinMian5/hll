"""
Abstract: Unit tests for taxonomy-classification persistence model projection.
Out of scope: Migration execution and runtime queue processing.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Index, Table, UniqueConstraint

from modules.taxonomy_classification.model import (
    TaxonomyClassificationJob,
    TaxonomyClassificationWebhookEvent,
    TaxonomyClassificationWebhookWakeup,
)
from shared.db.base import Base


def test_projection_registers_taxonomy_classification_tables() -> None:
    assert {
        "taxonomy_classification_jobs",
        "taxonomy_classification_webhook_events",
        "taxonomy_classification_webhook_wakeups",
    } <= set(Base.metadata.tables)


def test_jobs_projection_contains_job_id_unique_constraint() -> None:
    table = cast(Table, TaxonomyClassificationJob.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]

    assert {"job_id"} in unique_column_sets
    assert table.c.job_id.nullable is True


def test_jobs_projection_contains_active_only_partial_unique_index() -> None:
    table = cast(Table, TaxonomyClassificationJob.__table__)
    indexes = [index for index in table.indexes if isinstance(index, Index)]
    matching = [
        index
        for index in indexes
        if {column.name for column in index.columns}
        == {"scope_node_id", "source_unclassified_node_id", "node_id"}
        and index.unique
    ]

    assert matching
    predicate = str(matching[0].dialect_options["postgresql"]["where"])
    assert "processed_at IS NULL" in predicate
    assert "terminal_state IS NULL" in predicate


def test_webhook_events_projection_contains_idempotency_and_pending_indexes() -> None:
    table = cast(Table, TaxonomyClassificationWebhookEvent.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]
    index_column_sets = [{column.name for column in index.columns} for index in table.indexes]

    assert {"event_id"} in unique_column_sets
    assert {"processed_at", "created_at"} in index_column_sets


def test_webhook_wakeups_projection_uses_event_id_unique_constraint() -> None:
    table = cast(Table, TaxonomyClassificationWebhookWakeup.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]

    assert {"event_id"} in unique_column_sets
