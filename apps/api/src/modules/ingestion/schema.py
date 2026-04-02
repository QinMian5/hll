"""
Abstract: Transport models for ingestion request validation and accepted-response
payloads.
Out of scope: Queue dispatching and worker-side embedding execution.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
IngestionIdentifier = Annotated[
    str,
    StringConstraints(pattern=r"^ing_[0-9a-f]{32}$"),
]


class IngestionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: NonEmptyText
    content: NonEmptyText


class IngestionAcceptedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    accepted: Literal[True] = True
    ingestion_id: IngestionIdentifier
