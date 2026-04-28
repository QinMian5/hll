"""
Abstract: Dashboard usage-summary models for MCP-owned search usage events.
Out of scope: HTTP routing, service-token verification, and quota policy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_serializer

PatFingerprint = Annotated[str, StringConstraints(pattern=r"^pat_[0-9a-f]{64}$")]


class UsageSummaryRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pat_fingerprints: list[PatFingerprint] = Field(alias="patFingerprints", min_length=1)


class UsageSummaryRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pat_fingerprint: PatFingerprint = Field(alias="patFingerprint")
    successful_search_count: int = Field(alias="successfulSearchCount", ge=0)
    last_used_at: datetime | None = Field(default=None, alias="lastUsedAt")

    @field_serializer("last_used_at", when_used="json")
    def serialize_last_used_at(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat().replace("+00:00", "Z")


def dedupe_pat_fingerprints(pat_fingerprints: list[str]) -> list[str]:
    return list(dict.fromkeys(pat_fingerprints))
