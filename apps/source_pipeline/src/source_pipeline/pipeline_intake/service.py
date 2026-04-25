"""
Abstract: Intake materialization for workflow runs and units.
Out of scope: Queue submission and runtime polling behavior.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from source_pipeline.db.models import WorkflowRun, WorkflowUnit
from source_pipeline.page_to_card.contracts import SourceUnit


class PipelineIntakeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(
        self,
        *,
        source_kind: str,
        config_payload: dict[str, Any],
    ) -> WorkflowRun:
        raw_units = config_payload.get("units", [])
        run_config_payload = {key: value for key, value in config_payload.items() if key != "units"}
        run = WorkflowRun(
            source_kind=source_kind,
            config_payload=run_config_payload,
        )
        self._session.add(run)
        await self._session.flush()

        for raw_unit in raw_units:
            unit_payload = SourceUnit.model_validate(raw_unit).model_dump(mode="json")
            self._session.add(
                WorkflowUnit(
                    workflow_run_id=run.id,
                    source_kind=unit_payload["source_kind"],
                    source_ref=unit_payload["source_ref"],
                    payload=unit_payload,
                )
            )

        await self._session.commit()
        await self._session.refresh(run)
        return run
