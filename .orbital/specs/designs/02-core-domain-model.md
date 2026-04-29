---
abstract: Core data and domain model definition for V1 Node-Edge knowledge network, card versions, suggested edits, and adjacency-index read optimization.
out_of_scope: API endpoint contracts, SQL migration scripts, review-workbench UI, and large-scale partitioning strategy.
---

# Design: 02-core-domain-model

## Active Truth Policy
- This document defines only currently accepted V1 domain-model decisions.
- Superseded modeling choices are removed from active text.

## Context
- **Purpose:** Define the V1 persistent domain model for knowledge cards, card versions, suggested edits, and the read-optimized adjacency pattern.
- **Scope/Boundaries:** Covers `Node`, `CardVersion`, `CardSuggestedEdit`, `Edge`, and `Adjacency` persistence semantics and read query shape.
- **Related Requirements:** R-002, R-004, R-005, R-006.

## Domain Model Definition (SQLAlchemy v2)

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, ForeignKeyConstraint, Index, Integer, Text, UniqueConstraint, text
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
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

    edges: Mapped[list["Edge"]] = relationship(
        secondary="adjacency",
        primaryjoin="Node.id == Adjacency.node_id",
        secondaryjoin="Edge.id == Adjacency.edge_id",
        viewonly=True,
    )

    __table_args__ = (
        CheckConstraint("current_version >= 1", name="ck_nodes_current_version_positive"),
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
        CheckConstraint("version >= 1", name="ck_card_versions_version_positive"),
        UniqueConstraint("node_id", "version", name="uq_card_versions_node_version"),
        Index("ix_card_versions_node_id", "node_id"),
    )


class CardSuggestedEdit(Base):
    __tablename__ = "card_suggested_edits"

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(Integer, nullable=False)
    base_version: Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_title: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_content: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_by_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
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
        CheckConstraint("base_version >= 1", name="ck_card_suggested_edits_base_version_positive"),
        CheckConstraint("status IN ('pending', 'accepted', 'rejected')", name="ck_card_suggested_edits_status"),
        Index("ix_card_suggested_edits_node_id", "node_id"),
        Index("ix_card_suggested_edits_suggested_by_user_id", "suggested_by_user_id"),
        Index("ix_card_suggested_edits_status", "status"),
    )


class Edge(Base):
    __tablename__ = "edges"

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
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("node_a_id < node_b_id", name="ck_edges_canonical_pair"),
        CheckConstraint("strength >= 0.0 AND strength <= 1.0", name="ck_edges_strength_range"),
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
```

## Semantic Rules
- `Node` is the atomic knowledge unit.
- `Node.current_version` is a positive integer and equals the highest formal card version for that node.
- `CardVersion.version` is a positive integer scoped to one `Node`.
- `CardVersion` stores formal card history for audit, diff, and rollback baselines.
- `CardSuggestedEdit` stores proposed title/content values submitted by authenticated users.
- `CardSuggestedEdit.base_version` references the formal card version the user saw when preparing the suggestion.
- `CardSuggestedEdit.suggested_by_user_id` stores the authenticated Logto user id string.
- `CardSuggestedEdit.status` is one of `pending`, `accepted`, or `rejected`.
- `Node.embedding` is required and uses fixed dimension `1536`.
- `Edge` is an undirected relation between two distinct nodes.
- V1 stores one canonical edge per unordered node pair.
- `Edge.strength` uses normalized range `[0, 1]`.
- V1 initialization selects edges from title-mention and semantic candidate pools.
- Title-mention candidates are existing nodes whose normalized title appears as a complete normalized phrase in the new card content.
- Semantic candidates are selected by embedding similarity.
- Candidate budgets, semantic candidate pool size, and semantic strength threshold are runtime policy.
- V1 initialization rule for persisted strength is `strength = (dot_product + 1) / 2`.
- Edge initialization policy is not persisted as a transport field.

## Read Model
- V1 read result model is `Subgraph`.
- `Subgraph` contains only:
  - `nodes`
  - `edges`
- `Subgraph` excludes `edge_threshold`, `anchor`, and `stats`.

## Design Decisions

### Why This Design
- **Node + Edge as source of truth:** keeps domain semantics explicit and normalized.
- **CardVersion as formal card history:** gives suggested edits, audit, and rollback flows a stable card-content baseline without duplicating original content on every suggestion.
- **SuggestedEdit bound to `(node_id, base_version)`:** preserves the user's visible editing context while allowing the current card to advance independently.
- **Adjacency as physical index table:** optimizes read-heavy neighbor queries without changing domain truth.
- **Canonical unordered edge pair (`node_a_id < node_b_id`):** prevents duplicate mirrored edges and enforces undirected semantics at storage level.
- **Explicit `Node.edges` join through adjacency:** keeps query path deterministic and avoids ambiguous ORM join behavior.

### Why Not Alternative Choices
- **Not using `OR` query (`node_a_id = ? OR node_b_id = ?`) as primary path:** less predictable for large read-heavy workloads.
- **Not storing mirrored directional rows:** duplicates relation meaning and weakens canonical integrity.
- **Not keeping threshold as API/transport field:** threshold is internal selection policy, not returned domain payload in V1.
- **Not storing user name/email snapshots on suggested edits:** user identity display data remains owned by Logto-backed identity lookup rather than duplicated inside card suggestion records.
- **Not introducing partitioning/sharding or other large-scale mechanisms in V1:** exceeds MVP complexity goals.

## Validation
- PostgreSQL extension `vector` is enabled before applying vector-backed schema.
- Neighbor-query path can be expressed as `Node -> Adjacency(node_id index) -> Edge`.
- Card suggestion diff path can be expressed as `CardSuggestedEdit -> CardVersion(node_id, base_version)`.
- Unordered-edge uniqueness and no-self-loop constraints are enforced by database constraints.
- Card version uniqueness, positive versions, and suggestion status validity are enforced by database constraints.
- V1 documents only accepted current state and omits migration narration.
