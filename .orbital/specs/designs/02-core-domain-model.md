---
abstract: Core data and domain model definition for V1 Node-Edge knowledge network with adjacency-index read optimization.
out_of_scope: API endpoint contracts, SQL migration scripts, and large-scale partitioning strategy.
---

# Design: 02-core-domain-model

## Active Truth Policy
- This document defines only currently accepted V1 domain-model decisions.
- Superseded modeling choices are removed from active text.

## Context
- **Purpose:** Define the V1 persistent domain model and the read-optimized adjacency pattern.
- **Scope/Boundaries:** Covers `Node`, `Edge`, and `Adjacency` persistence semantics and read query shape.
- **Related Requirements:** R-002, R-004, R-005, R-006.

## Domain Model Definition (SQLAlchemy v2)

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
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
- `Node.embedding` is required and uses fixed dimension `1536`.
- `Edge` is an undirected relation between two distinct nodes.
- V1 stores one canonical edge per unordered node pair.
- `Edge.strength` uses normalized range `[0, 1]`.
- V1 initialization rule is `strength = (dot_product + 1) / 2`.
- V1 edge materialization threshold is runtime-configurable via `KNOWLEDGE_API_EDGE_SIMILARITY_MIN_STRENGTH`.
- Threshold is a business rule and is not persisted as a transport field.

## Read Model
- V1 read result model is `Subgraph`.
- `Subgraph` contains only:
  - `nodes`
  - `edges`
- `Subgraph` excludes `edge_threshold`, `anchor`, and `stats`.

## Design Decisions

### Why This Design
- **Node + Edge as source of truth:** keeps domain semantics explicit and normalized.
- **Adjacency as physical index table:** optimizes read-heavy neighbor queries without changing domain truth.
- **Canonical unordered edge pair (`node_a_id < node_b_id`):** prevents duplicate mirrored edges and enforces undirected semantics at storage level.
- **Explicit `Node.edges` join through adjacency:** keeps query path deterministic and avoids ambiguous ORM join behavior.

### Why Not Alternative Choices
- **Not using `OR` query (`node_a_id = ? OR node_b_id = ?`) as primary path:** less predictable for large read-heavy workloads.
- **Not storing mirrored directional rows:** duplicates relation meaning and weakens canonical integrity.
- **Not keeping threshold as API/transport field:** threshold is internal selection policy, not returned domain payload in V1.
- **Not introducing partitioning/sharding or other large-scale mechanisms in V1:** exceeds MVP complexity goals.

## Validation
- PostgreSQL extension `vector` is enabled before applying vector-backed schema.
- Neighbor-query path can be expressed as `Node -> Adjacency(node_id index) -> Edge`.
- Unordered-edge uniqueness and no-self-loop constraints are enforced by database constraints.
- V1 documents only accepted current state and omits migration narration.
