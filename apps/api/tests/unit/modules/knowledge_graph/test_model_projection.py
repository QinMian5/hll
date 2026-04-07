"""
Abstract: Unit tests for knowledge-graph persistence schema projection.
Out of scope: Migration execution and runtime database I/O behavior.
"""

from __future__ import annotations

from typing import cast

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, Table

from modules.knowledge_graph.model import Adjacency, Edge, Node
from shared.db.base import Base


def test_projection_registers_required_tables() -> None:
    table_names = set(Base.metadata.tables)
    assert {"nodes", "edges", "adjacency"} <= table_names


def test_nodes_embedding_is_vector_1536() -> None:
    embedding_type = Node.__table__.c.embedding.type
    assert isinstance(embedding_type, Vector)
    assert embedding_type.dim == 1536


def test_edges_constraints_present() -> None:
    edge_table = cast(Table, Edge.__table__)
    constraints = edge_table.constraints
    constraint_names = {constraint.name for constraint in constraints}
    assert "ck_edges_canonical_pair" in constraint_names
    assert "ck_edges_strength_range" in constraint_names
    assert "uq_edges_unordered_pair" in constraint_names

    check_expressions = {
        str(constraint.sqltext).replace(" ", "").lower()
        for constraint in constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert any("node_a_id<node_b_id" in expression for expression in check_expressions)
    assert any(
        "strength>=0.0" in expression and "strength<=1.0" in expression
        for expression in check_expressions
    )


def test_node_and_edge_required_columns_and_edges_relation_contract() -> None:
    assert Node.__table__.c.title.nullable is False
    assert Node.__table__.c.content.nullable is False
    assert Edge.__table__.c.strength.nullable is False

    edges_relation = Node.edges.property
    assert edges_relation.viewonly is True
    assert edges_relation.secondary is not None
    assert edges_relation.secondary.name == "adjacency"
    assert edges_relation.primaryjoin is not None
    assert edges_relation.secondaryjoin is not None


def test_node_and_edge_timestamp_columns_are_present_and_required() -> None:
    for table in (Node.__table__, Edge.__table__):
        created_at_column = table.c.created_at
        updated_at_column = table.c.updated_at

        created_at_type = created_at_column.type
        updated_at_type = updated_at_column.type

        assert isinstance(created_at_type, DateTime)
        assert isinstance(updated_at_type, DateTime)
        assert created_at_type.timezone is True
        assert updated_at_type.timezone is True
        assert created_at_column.nullable is False
        assert updated_at_column.nullable is False


def test_edges_foreign_keys_use_cascade_delete() -> None:
    for column_name in ("node_a_id", "node_b_id"):
        column = Edge.__table__.c[column_name]
        foreign_keys = list(column.foreign_keys)
        assert len(foreign_keys) == 1
        foreign_key = foreign_keys[0]
        assert foreign_key.target_fullname == "nodes.id"
        assert foreign_key.ondelete == "CASCADE"


def test_adjacency_composite_pk_and_indexes() -> None:
    table = cast(Table, Adjacency.__table__)
    pk_column_names = {column.name for column in table.primary_key.columns}
    assert pk_column_names == {"node_id", "edge_id"}

    index_names = {index.name for index in table.indexes}
    assert "ix_adjacency_node_id" in index_names
    assert "ix_adjacency_edge_id" in index_names


def test_adjacency_timestamp_columns_are_present_and_required() -> None:
    created_at_column = Adjacency.__table__.c.created_at
    updated_at_column = Adjacency.__table__.c.updated_at

    created_at_type = created_at_column.type
    updated_at_type = updated_at_column.type

    assert isinstance(created_at_type, DateTime)
    assert isinstance(updated_at_type, DateTime)
    assert created_at_type.timezone is True
    assert updated_at_type.timezone is True
    assert created_at_column.nullable is False
    assert updated_at_column.nullable is False


def test_adjacency_foreign_keys_use_cascade_delete() -> None:
    for column_name, target in (("node_id", "nodes.id"), ("edge_id", "edges.id")):
        column = Adjacency.__table__.c[column_name]
        foreign_keys = list(column.foreign_keys)
        assert len(foreign_keys) == 1
        foreign_key = foreign_keys[0]
        assert foreign_key.target_fullname == target
        assert foreign_key.ondelete == "CASCADE"
