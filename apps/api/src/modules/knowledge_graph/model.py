"""
Abstract: SQLAlchemy persistence projection for knowledge graph Node/Edge/Adjacency.
Out of scope: Service-layer business workflow and API transport contracts.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    edges: Mapped[list[Edge]] = relationship(
        secondary="adjacency",
        primaryjoin="Node.id == Adjacency.node_id",
        secondaryjoin="Edge.id == Adjacency.edge_id",
        viewonly=True,
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

    __table_args__ = (
        Index("ix_adjacency_node_id", "node_id"),
        Index("ix_adjacency_edge_id", "edge_id"),
    )
