"""
Abstract: Integration tests for source-pipeline intake materialization.
Out of scope: Queue transport behavior and downstream review fan-out logic.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source_pipeline.db.models import WorkflowUnit
from source_pipeline.pipeline_intake.service import PipelineIntakeService

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


async def test_materialize_config_creates_run_and_units(db_session: AsyncSession) -> None:
    service = PipelineIntakeService(db_session)

    run = await service.create_run(
        source_kind="external",
        config_payload={
            "units": [
                {
                    "source_kind": "external",
                    "source_ref": "a",
                    "title": "A",
                    "content": "x",
                    "metadata": {"url": "https://example.com/a"},
                }
            ]
        },
    )

    assert run.id == 1
    units = list(
        (
            await db_session.execute(
                select(WorkflowUnit).where(WorkflowUnit.workflow_run_id == run.id)
            )
        ).scalars()
    )
    assert len(units) == 1
    assert units[0].page_to_card_job_id is None
