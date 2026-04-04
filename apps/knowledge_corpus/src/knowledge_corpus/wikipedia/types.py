"""
Abstract: Stable Wikipedia schema constants for the knowledge corpus app.
Out of scope: Runtime repository behavior and query orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

WIKIPEDIA_SCHEMA = "wikipedia"
WIKIPEDIA_DOCUMENTS_TABLE = "documents"
WIKIPEDIA_PROCESSED_DOCUMENTS_TABLE = "processed_documents"


@dataclass(slots=True, frozen=True)
class WikipediaDocumentRecord:
    page_id: int
    url: str
    title: str
    clean_text: str


@dataclass(slots=True, frozen=True)
class WikipediaProcessedDocumentRecord:
    page_id: int
    processed_at: datetime
    external_target_ref: str


@dataclass(slots=True, frozen=True)
class WikipediaSearchResult:
    page_id: int
    url: str
    title: str
    clean_text: str
    rank: float
