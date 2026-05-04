"""
Abstract: Tests for science page submission into source-pipeline intake.
Out of scope: Live corpus queries and production job queue submission.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_operator.source_pipeline.submit_science_pages import (
    CorpusPageRecord,
    ExistingWorkflowUnitsError,
    PageSelection,
    build_source_unit,
    ensure_no_existing_source_refs,
    materialize_intake,
    parse_science_query_batch_yaml_subset,
)

pytestmark = pytest.mark.anyio


def test_build_source_unit_maps_wikipedia_page_metadata() -> None:
    page = CorpusPageRecord(
        page_id=42,
        url="https://en.wikipedia.org/wiki/Quadratic_equation",
        title="Quadratic equation",
        clean_text="A quadratic equation is a polynomial equation of degree two.",
    )
    selection = PageSelection(page=page, batch_name="mathematics-core", rank=0.75)

    unit = build_source_unit(selection)

    assert unit == {
        "source_kind": "wikipedia",
        "source_ref": "wikipedia:42",
        "title": "Quadratic equation",
        "content": "A quadratic equation is a polynomial equation of degree two.",
        "metadata": {
            "page_id": 42,
            "url": "https://en.wikipedia.org/wiki/Quadratic_equation",
            "selection_batch": "mathematics-core",
            "selection_rank": 0.75,
        },
    }


async def test_materialize_intake_dry_run_does_not_open_source_pipeline_session() -> None:
    def fail_if_called() -> AsyncSession:
        raise AssertionError("dry-run must not open a source-pipeline session")

    summary = await materialize_intake(
        units=[
            {
                "source_kind": "wikipedia",
                "source_ref": "wikipedia:42",
                "title": "Quadratic equation",
                "content": "A quadratic equation is a polynomial equation of degree two.",
                "metadata": {},
            }
        ],
        config_payload={"batches": []},
        submit=False,
        session_factory=fail_if_called,
    )

    assert summary.submitted is False
    assert summary.workflow_run_id is None
    assert summary.unit_count == 1


def test_existing_source_refs_are_rejected_before_submission() -> None:
    with pytest.raises(ExistingWorkflowUnitsError, match="wikipedia:42"):
        ensure_no_existing_source_refs({"wikipedia:42"})


def test_parse_science_query_batch_yaml_subset_supports_runtime_image() -> None:
    payload = parse_science_query_batch_yaml_subset(
        """
batches:
  - name: mathematics-core
    query: mathematics algebra geometry
    limit: 1000
"""
    )

    assert payload == {
        "batches": [
            {
                "name": "mathematics-core",
                "query": "mathematics algebra geometry",
                "limit": 1000,
            }
        ]
    }
