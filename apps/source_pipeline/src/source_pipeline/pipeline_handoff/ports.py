"""
Abstract: Narrow downstream handoff protocol for review-accepted cards.
Out of scope: Concrete transport implementations and retry policy.
"""

from __future__ import annotations

from typing import Protocol

from source_pipeline.page_to_card.contracts import CardDraft


class AcceptedCardHandoffPort(Protocol):
    async def handoff(
        self,
        *,
        candidate_id: int,
        card: CardDraft,
    ) -> None: ...
