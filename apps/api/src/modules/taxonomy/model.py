"""
Abstract: SQLAlchemy persistence projection for taxonomy tree, assignments, and layout read models.
Out of scope: Import orchestration and HTTP transport contracts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base


class TaxonomyNode(Base):
    __tablename__ = "taxonomy_nodes"
    __table_args__ = (
        CheckConstraint("depth >= 0", name="depth_non_negative"),
        CheckConstraint("route_slug <> ''", name="route_slug_non_empty"),
        UniqueConstraint("parent_id", "name", name="uq_taxonomy_nodes_parent_name"),
        UniqueConstraint(
            "parent_id",
            "route_slug",
            name="uq_taxonomy_nodes_parent_route_slug",
        ),
        Index(
            "uq_taxonomy_nodes_single_root",
            text("(COALESCE(parent_id, 0))"),
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index(
            "uq_taxonomy_nodes_parent_lower_name",
            "parent_id",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("taxonomy_nodes.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    route_slug: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)


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


class TaxonomyScopeProjectionEdge(Base):
    __tablename__ = "taxonomy_scope_projection_edges"
    __table_args__ = (
        Index("ix_taxonomy_scope_projection_edges_edge_id", "edge_id"),
        Index(
            "ix_taxonomy_scope_projection_edges_scope",
            "scope_kind",
            "taxonomy_node_id",
        ),
    )

    scope_kind: Mapped[str] = mapped_column(Text, primary_key=True)
    taxonomy_node_id: Mapped[int] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    edge_id: Mapped[int] = mapped_column(
        ForeignKey("edges.id", ondelete="CASCADE"),
        primary_key=True,
    )


class TaxonomyCardScopeLayout(Base):
    __tablename__ = "taxonomy_card_scope_layouts"
    __table_args__ = (
        CheckConstraint(
            "scope_kind IN ('taxonomy_node', 'virtual_unclassified')",
            name="taxonomy_card_scope_layouts_scope_kind",
        ),
        UniqueConstraint(
            "scope_kind",
            "taxonomy_node_id",
            "layout_version",
            name="uq_taxonomy_card_scope_layouts_scope_version",
        ),
        Index(
            "ix_taxonomy_card_scope_layouts_scope",
            "scope_kind",
            "taxonomy_node_id",
        ),
        Index("ix_taxonomy_card_scope_layouts_input_fingerprint", "input_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_kind: Mapped[str] = mapped_column(Text, nullable=False)
    taxonomy_node_id: Mapped[int] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    layout_version: Mapped[str] = mapped_column(Text, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    layout_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TaxonomyCardScopeLayoutComputeRequest(Base):
    __tablename__ = "taxonomy_card_scope_layout_compute_requests"
    __table_args__ = (
        CheckConstraint(
            "scope_kind IN ('taxonomy_node', 'virtual_unclassified')",
            name="taxonomy_card_scope_layout_compute_requests_scope_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="taxonomy_card_scope_layout_compute_requests_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="taxonomy_card_scope_layout_compute_requests_attempt_count",
        ),
        UniqueConstraint(
            "scope_kind",
            "taxonomy_node_id",
            "layout_version",
            name="uq_taxonomy_card_scope_layout_compute_requests_scope_version",
        ),
        Index(
            "ix_taxonomy_card_scope_layout_compute_requests_status_requested",
            "status",
            "requested_at",
        ),
        Index(
            "ix_taxonomy_card_scope_layout_compute_requests_scope",
            "scope_kind",
            "taxonomy_node_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_kind: Mapped[str] = mapped_column(Text, nullable=False)
    taxonomy_node_id: Mapped[int] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    layout_version: Mapped[str] = mapped_column(Text, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
