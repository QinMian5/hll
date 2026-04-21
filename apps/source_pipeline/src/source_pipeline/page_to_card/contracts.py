"""
Abstract: Pydantic contracts for the page-to-card step.
Out of scope: Queue transport behavior and downstream review orchestration.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class SourceUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: str
    source_ref: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CardDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    content: str


CARD_DRAFT_LIST_ADAPTER = TypeAdapter(list[CardDraft])


def export_page_to_card_output_schema() -> dict[str, Any]:
    return CARD_DRAFT_LIST_ADAPTER.json_schema()
