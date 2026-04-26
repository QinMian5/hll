"""
Abstract: Pydantic contracts for job-queue webhook notification intake.
Out of scope: HTTP authentication and runtime event processing behavior.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

WebhookEventType = Literal["result.accepted", "job.terminal_non_accepted"]


class JobQueueWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    event_type: WebhookEventType
    job_id: PositiveInt
    queue_name: str = Field(min_length=1)
    occurred_at: datetime
    submission_id: PositiveInt | None = None
    terminal_state: Literal["DEAD_LETTER"] | None = None

    @model_validator(mode="after")
    def validate_event_shape(self) -> JobQueueWebhookPayload:
        if self.event_type == "result.accepted" and self.submission_id is None:
            raise ValueError("result.accepted webhook payloads require submission_id")
        if self.event_type == "job.terminal_non_accepted" and self.terminal_state != "DEAD_LETTER":
            raise ValueError(
                "job.terminal_non_accepted webhook payloads require terminal_state=DEAD_LETTER"
            )
        return self


__all__ = ["JobQueueWebhookPayload", "WebhookEventType"]
