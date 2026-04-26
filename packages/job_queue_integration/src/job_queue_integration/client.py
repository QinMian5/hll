"""
Abstract: Shared HTTP client for job-queue producer and results surfaces.
Out of scope: Domain-specific orchestration and local persistence.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict

type JsonObject = dict[str, Any]
type JsonMapping = Mapping[str, object]
type JobPriority = Literal["low", "normal", "high", "critical"]


class AccessTokenProvider(Protocol):
    async def get_access_token(self) -> str: ...

    async def aclose(self) -> None: ...


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
        token_provider: AccessTokenProvider,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token_provider = token_provider
        self._client = httpx.AsyncClient(base_url=base_url, transport=transport)

    async def create_job(
        self,
        *,
        queue_name: str,
        priority: JobPriority,
        instruction: str,
        output_schema: JsonMapping,
        payload: JsonMapping | None = None,
        metadata: JsonMapping | None = None,
    ) -> int:
        access_token = await self._token_provider.get_access_token()
        response = await self._client.post(
            "/producer/jobs",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "queue_name": queue_name,
                "priority": priority,
                "instruction": instruction,
                "output_schema": dict(output_schema),
                "payload": dict(payload or {}),
                "metadata": dict(metadata or {}),
            },
        )
        response.raise_for_status()
        return int(response.json()["job_id"])

    async def get_result(self, *, job_id: int) -> JobResult:
        access_token = await self._token_provider.get_access_token()
        response = await self._client.get(
            f"/results/{job_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 202:
            return NotReadyJobResult.model_validate(response.json())

        response.raise_for_status()
        return AcceptedJobResult.model_validate(response.json())

    async def aclose(self) -> None:
        await self._client.aclose()
        await self._token_provider.aclose()


__all__ = [
    "AcceptedJobResult",
    "AccessTokenProvider",
    "JobQueueClient",
    "JobResult",
    "JsonMapping",
    "JsonObject",
    "NotReadyJobResult",
]
