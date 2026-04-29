"""
Abstract: SQLAlchemy persistence projection for taxonomy tree nodes and final assignments.
Out of scope: Import orchestration and HTTP transport contracts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base


class TaxonomyNode(Base):
    __tablename__ = "taxonomy_nodes"
    __table_args__ = (
        CheckConstraint("depth >= 0", name="depth_non_negative"),
        UniqueConstraint("parent_id", "name", name="uq_taxonomy_nodes_parent_name"),
        Index(
            "uq_taxonomy_nodes_single_root",
            text("(COALESCE(parent_id, 0))"),
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("taxonomy_nodes.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    is_leaf: Mapped[bool] = mapped_column(Boolean, nullable=False)


class NodeTaxonomyAssignment(Base):
    __tablename__ = "node_taxonomy_assignments"
    __table_args__ = (
        UniqueConstraint("node_id", name="uq_node_taxonomy_assignments_node_id"),
        Index("ix_node_taxonomy_assignments_taxonomy_node_id", "taxonomy_node_id"),
        Index(
            "ix_node_taxonomy_assignments_taxonomy_node_id_node_id",
            "taxonomy_node_id",
            "node_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    taxonomy_node_id: Mapped[int] = mapped_column(
        ForeignKey("taxonomy_nodes.id"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class TaxonomyLeafProjectionEdge(Base):
    __tablename__ = "taxonomy_leaf_projection_edges"
    __table_args__ = (Index("ix_taxonomy_leaf_projection_edges_edge_id", "edge_id"),)

    leaf_id: Mapped[int] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    edge_id: Mapped[int] = mapped_column(
        ForeignKey("edges.id", ondelete="CASCADE"),
        primary_key=True,
    )
