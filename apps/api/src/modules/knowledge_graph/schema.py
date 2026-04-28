"""
Abstract: Pydantic HTTP schemas for private knowledge-graph card suggestion routes.
Out of scope: Browser session handling and persistence models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SuggestedEditCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_version: int = Field(gt=0)
    suggested_title: NonEmptyString
    suggested_content: NonEmptyString


class SuggestedEditCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    node_id: int = Field(gt=0)
    base_version: int = Field(gt=0)
    status: Literal["pending", "accepted", "rejected"]
    created_at: datetime
