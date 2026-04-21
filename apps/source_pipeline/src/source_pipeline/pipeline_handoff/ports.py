"""
Abstract: Narrow downstream handoff protocol for accepted review results.
Out of scope: Concrete transport implementations and retry policy.
"""

from __future__ import annotations

from typing import Protocol

from source_pipeline.card_review.contracts import ReviewResult
from source_pipeline.page_to_card.contracts import CardDraft


class ReviewHandoffPort(Protocol):
    async def handoff(
        self,
        *,
        workflow_unit_id: int,
        ordinal: int,
        card: CardDraft,
        review: ReviewResult,
    ) -> None: ...
