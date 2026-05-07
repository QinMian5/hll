"""
Abstract: SQLAlchemy persistence projection for knowledge graph nodes, card versions,
card proposals, reviewer audit records, edges, and adjacency.
Out of scope: Service-layer business workflow and API transport contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    FetchedValue,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base

NODE_SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(content, '')), 'B')"
)


class Node(Base):
    __tablename__ = "nodes"
    __mapper_args__: ClassVar[dict[str, bool]] = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    current_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
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
        onupdate=func.now(),
        server_onupdate=FetchedValue(),
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
        CheckConstraint(
            "lifecycle_state IN ('active', 'archived')",
            name="lifecycle_state",
        ),
        Index("ix_nodes_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_nodes_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )


class CardVersion(Base):
    __tablename__ = "card_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
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


class WorkspaceRole(Base):
    __tablename__ = "workspace_roles"
    __mapper_args__: ClassVar[dict[str, bool]] = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    granted_by_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    revoked_by_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        server_onupdate=FetchedValue(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("role IN ('reviewer', 'admin')", name="role"),
        Index("ix_workspace_roles_user_id", "user_id"),
        Index("ix_workspace_roles_role", "role"),
        Index(
            "uq_workspace_roles_active_user_role",
            "user_id",
            "role",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )


class CardProposal(Base):
    __tablename__ = "card_proposals"
    __mapper_args__: ClassVar[dict[str, bool]] = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending_review",
        server_default=text("'pending_review'"),
    )
    submitted_by_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        server_onupdate=FetchedValue(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "proposal_type IN ('create', 'edit', 'delete')",
            name="proposal_type",
        ),
        CheckConstraint(
            "status IN ('pending_review', 'accepted_applied', 'rejected', 'withdrawn')",
            name="status",
        ),
        CheckConstraint("btrim(reason) <> ''", name="reason_nonempty"),
        Index("ix_card_proposals_submitted_by_user_id", "submitted_by_user_id"),
        Index("ix_card_proposals_reviewed_by_user_id", "reviewed_by_user_id"),
        Index("ix_card_proposals_status", "status"),
        Index("ix_card_proposals_proposal_type", "proposal_type"),
    )


class ProposalApplyAudit(Base):
    __tablename__ = "proposal_apply_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("card_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    proposal_type: Mapped[str] = mapped_column(Text, nullable=False)
    affected_node_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    created_versions: Mapped[list[dict[str, int]]] = mapped_column(JSONB, nullable=False)
    archive_outcome: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_proposal_apply_audits_proposal_id", "proposal_id"),
        Index("ix_proposal_apply_audits_reviewer_user_id", "reviewer_user_id"),
        Index("ix_proposal_apply_audits_proposal_type", "proposal_type"),
    )


class Edge(Base):
    __tablename__ = "edges"
    __mapper_args__: ClassVar[dict[str, bool]] = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
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
        onupdate=func.now(),
        server_onupdate=FetchedValue(),
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
    __mapper_args__: ClassVar[dict[str, bool]] = {"eager_defaults": True}

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
        onupdate=func.now(),
        server_onupdate=FetchedValue(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_adjacency_node_id", "node_id"),
        Index("ix_adjacency_edge_id", "edge_id"),
    )
