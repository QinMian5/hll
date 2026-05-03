"""
Abstract: Pydantic HTTP schemas for private knowledge-graph proposal routes.
Out of scope: Browser session handling and persistence models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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


CardProposalType = Literal["create", "edit", "delete"]
CardProposalStatus = Literal["pending_review", "accepted_applied", "rejected", "withdrawn"]


class CardProposalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_type: CardProposalType
    proposed_title: NonEmptyString | None = None
    proposed_content: NonEmptyString | None = None
    target_node_id: int | None = Field(default=None, gt=0)
    base_version: int | None = Field(default=None, gt=0)
    suggested_title: NonEmptyString | None = None
    suggested_content: NonEmptyString | None = None
    reason: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_payload_for_type(self) -> CardProposalCreateRequest:
        if self.proposal_type == "create":
            if self.proposed_title is None or self.proposed_content is None:
                raise ValueError("Create proposals require proposed_title and proposed_content.")
            return self

        if self.target_node_id is None or self.base_version is None:
            raise ValueError("Card proposals require target_node_id and base_version.")

        if self.proposal_type == "edit":
            if self.suggested_title is None or self.suggested_content is None:
                raise ValueError("Edit proposals require suggested_title and suggested_content.")
            return self

        if self.reason is None:
            raise ValueError("Delete proposals require reason.")
        return self


class CardProposalReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_note: NonEmptyString | None = None


class CardProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    proposal_type: CardProposalType
    status: CardProposalStatus
    submitted_by_user_id: NonEmptyString
    reviewed_by_user_id: NonEmptyString | None
    review_note: str | None
    payload: dict[str, object]
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None


class CardProposalListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[CardProposalResponse]
