"""
Abstract: Dashboard quota-summary request and response models.
Out of scope: HTTP routing, service-token verification, and Redis persistence.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from knowledge_mcp.quota.store import QuotaSummary, QuotaWindowSnapshot


class QuotaSummaryRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_sub: str = Field(alias="userSub", min_length=1)


class QuotaWindowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    used: int = Field(ge=0)
    limit: int = Field(ge=0)
    remaining: int = Field(ge=0)
    window_seconds: int = Field(alias="windowSeconds", ge=1)
    started_at: datetime | None = Field(alias="startedAt")
    reset_at: datetime | None = Field(alias="resetAt")

    @classmethod
    def from_snapshot(cls, snapshot: QuotaWindowSnapshot) -> QuotaWindowResponse:
        return cls(
            used=snapshot.used,
            limit=snapshot.limit,
            remaining=snapshot.remaining,
            windowSeconds=snapshot.window_seconds,
            startedAt=snapshot.started_at,
            resetAt=snapshot.reset_at,
        )

    @field_serializer("started_at", "reset_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat().replace("+00:00", "Z")


class QuotaResponseBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    daily: QuotaWindowResponse
    weekly: QuotaWindowResponse

    @classmethod
    def from_summary(cls, summary: QuotaSummary) -> QuotaResponseBody:
        return cls(
            daily=QuotaWindowResponse.from_snapshot(summary.daily),
            weekly=QuotaWindowResponse.from_snapshot(summary.weekly),
        )


class QuotaSummaryResponse(BaseModel):
    quota: QuotaResponseBody

    @classmethod
    def from_summary(cls, summary: QuotaSummary) -> QuotaSummaryResponse:
        return cls(quota=QuotaResponseBody.from_summary(summary))
