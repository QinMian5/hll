"""
Abstract: Pydantic response models for the search HTTP contract.
Out of scope: Search orchestration logic and knowledge-domain persistence models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MatchedCardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    content: str


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched_cards: list[MatchedCardResponse]
    connected_titles: list[str]
