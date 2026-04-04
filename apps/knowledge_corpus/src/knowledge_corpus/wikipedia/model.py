"""
Abstract: SQLAlchemy model projection for Wikipedia source and processed documents.
Out of scope: Repository query behavior and external source orchestration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Computed, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_corpus.db.base import Base
from knowledge_corpus.wikipedia.types import (
    WIKIPEDIA_DOCUMENTS_TABLE,
    WIKIPEDIA_PROCESSED_DOCUMENTS_TABLE,
    WIKIPEDIA_SCHEMA,
)

SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(clean_text, '')), 'B')"
)


class WikipediaDocument(Base):
    __tablename__ = WIKIPEDIA_DOCUMENTS_TABLE
    __table_args__ = (
        Index(
            "ix_wikipedia_documents_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        {"schema": WIKIPEDIA_SCHEMA},
    )

    page_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    clean_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(SEARCH_VECTOR_SQL, persisted=True),
        nullable=False,
    )


class WikipediaProcessedDocument(Base):
    __tablename__ = WIKIPEDIA_PROCESSED_DOCUMENTS_TABLE
    __table_args__ = ({"schema": WIKIPEDIA_SCHEMA},)

    page_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{WIKIPEDIA_SCHEMA}.{WIKIPEDIA_DOCUMENTS_TABLE}.page_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    processed_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("now()"))
    external_target_ref: Mapped[str] = mapped_column(String, nullable=False)
