"""
Abstract: Thin HTTP client for the job-queue producer and results surfaces.
Out of scope: Orchestrator state transitions and operator-history reads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict

type JsonObject = dict[str, Any]
type JobPriority = Literal["low", "normal", "high", "critical"]


class AcceptedJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["accepted"] = "accepted"
    job_id: int
    submission_id: int
    received_at: datetime
    result_payload: JsonObject


class NotReadyJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["not_ready"] = "not_ready"
    job_id: int
    state: str
    result_ready: Literal[False] = False


type JobResult = AcceptedJobResult | NotReadyJobResult


class JobQueueClient:
    def __init__(
        self,
        *,
        base_url: str,
        producer_token: str,
        results_reader_token: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._producer_token = producer_token
        self._results_reader_token = results_reader_token
        self._client = httpx.AsyncClient(
            base_url=base_url,
            transport=transport,
        )

    async def create_job(
        self,
        *,
        queue_name: str,
        priority: JobPriority,
        instruction: str,
        output_schema: JsonObject,
        payload: JsonObject | None = None,
        metadata: JsonObject | None = None,
    ) -> int:
        response = await self._client.post(
            "/producer/jobs",
            headers={"Authorization": f"Bearer {self._producer_token}"},
            json={
                "queue_name": queue_name,
                "priority": priority,
                "instruction": instruction,
                "output_schema": output_schema,
                "payload": payload or {},
                "metadata": metadata or {},
            },
        )
        response.raise_for_status()
        return int(response.json()["job_id"])

    async def get_result(self, *, job_id: int) -> JobResult:
        response = await self._client.get(
            f"/results/{job_id}",
            headers={"Authorization": f"Bearer {self._results_reader_token}"},
        )
        if response.status_code == 202:
            return NotReadyJobResult.model_validate(response.json())

        response.raise_for_status()
        return AcceptedJobResult.model_validate(response.json())

    async def aclose(self) -> None:
        await self._client.aclose()
