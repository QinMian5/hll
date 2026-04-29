"""
Abstract: SQLAlchemy persistence projection for knowledge graph nodes, card versions,
suggested edits, edges, and adjacency.
Out of scope: Service-layer business workflow and API transport contracts.
"""

from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base

NODE_SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(content, '')), 'B')"
)


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    current_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(NODE_SEARCH_VECTOR_SQL, persisted=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    edges: Mapped[list[Edge]] = relationship(
        secondary="adjacency",
        primaryjoin="Node.id == Adjacency.node_id",
        secondaryjoin="Edge.id == Adjacency.edge_id",
        viewonly=True,
    )

    __table_args__ = (
        CheckConstraint("current_version >= 1", name="current_version_positive"),
        Index("ix_nodes_search_vector", "search_vector", postgresql_using="gin"),
    )


class CardVersion(Base):
    __tablename__ = "card_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        UniqueConstraint("node_id", "version", name="uq_card_versions_node_version"),
        Index("ix_card_versions_node_id", "node_id"),
    )


class CardSuggestedEdit(Base):
    __tablename__ = "card_suggested_edits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    base_version: Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_title: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_content: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_by_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["node_id", "base_version"],
            ["card_versions.node_id", "card_versions.version"],
            name="fk_card_suggested_edits_base_version",
            ondelete="CASCADE",
        ),
        CheckConstraint("base_version >= 1", name="base_version_positive"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="status",
        ),
        Index("ix_card_suggested_edits_node_id", "node_id"),
        Index("ix_card_suggested_edits_suggested_by_user_id", "suggested_by_user_id"),
        Index("ix_card_suggested_edits_status", "status"),
    )


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_a_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_b_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("node_a_id < node_b_id", name="canonical_pair"),
        CheckConstraint(
            "strength >= 0.0 AND strength <= 1.0",
            name="strength_range",
        ),
        UniqueConstraint("node_a_id", "node_b_id", name="uq_edges_unordered_pair"),
    )


class Adjacency(Base):
    __tablename__ = "adjacency"

    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    edge_id: Mapped[int] = mapped_column(
        ForeignKey("edges.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_adjacency_node_id", "node_id"),
        Index("ix_adjacency_edge_id", "edge_id"),
    )
