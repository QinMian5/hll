"""
Abstract: Unit tests for knowledge-graph persistence schema projection.
Out of scope: Migration execution and runtime database I/O behavior.
"""

from __future__ import annotations

from typing import cast

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR

from modules.knowledge_graph.model import Adjacency, CardSuggestedEdit, CardVersion, Edge, Node
from shared.db.base import Base


def test_projection_registers_required_tables() -> None:
    table_names = set(Base.metadata.tables)
    assert {"nodes", "card_versions", "card_suggested_edits", "edges", "adjacency"} <= table_names


def test_nodes_embedding_is_vector_1536() -> None:
    embedding_type = Node.__table__.c.embedding.type
    assert isinstance(embedding_type, Vector)
    assert embedding_type.dim == 1536


def test_nodes_projection_contains_weighted_search_vector() -> None:
    table = cast(Table, Node.__table__)
    indexes_by_name = {index.name: index for index in table.indexes}

    assert "search_vector" in table.c
    assert isinstance(table.c.search_vector.type, TSVECTOR)
    assert table.c.search_vector.nullable is False
    assert "ix_nodes_search_vector" in indexes_by_name
    assert indexes_by_name["ix_nodes_search_vector"].dialect_options["postgresql"]["using"] == "gin"


def test_nodes_current_version_is_required_positive_integer() -> None:
    current_version = Node.__table__.c.current_version
    assert current_version.nullable is False
    assert isinstance(current_version.type, type(Edge.__table__.c.id.type))

    constraint_names = {constraint.name for constraint in Node.__table__.constraints}
    assert "ck_nodes_current_version_positive" in constraint_names


def test_card_versions_projection_contains_history_fields_and_constraints() -> None:
    table = cast(Table, CardVersion.__table__)
    column_names = set(table.c)
    constraint_names = {constraint.name for constraint in table.constraints}
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]
    index_names = {index.name for index in table.indexes}

    assert {"id", "node_id", "version", "title", "content", "created_at"} <= {
        column.name for column in column_names
    }
    assert table.c.node_id.nullable is False
    assert table.c.version.nullable is False
    assert "ck_card_versions_version_positive" in constraint_names
    assert {"node_id", "version"} in unique_column_sets
    assert "ix_card_versions_node_id" in index_names

    foreign_keys = list(table.c.node_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "nodes.id"
    assert foreign_keys[0].ondelete == "CASCADE"


def test_card_suggested_edits_projection_contains_status_and_base_version_constraints() -> None:
    table = cast(Table, CardSuggestedEdit.__table__)
    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}
    composite_foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "fk_card_suggested_edits_base_version"
    ]

    assert {
        "id",
        "node_id",
        "base_version",
        "suggested_title",
        "suggested_content",
        "suggested_by_user_id",
        "status",
        "created_at",
        "updated_at",
    } <= {column.name for column in table.c}
    assert "ck_card_suggested_edits_base_version_positive" in constraint_names
    assert "ck_card_suggested_edits_status" in constraint_names
    assert {"ix_card_suggested_edits_node_id", "ix_card_suggested_edits_status"} <= index_names
    assert "ix_card_suggested_edits_suggested_by_user_id" in index_names
    assert len(composite_foreign_keys) == 1
    assert composite_foreign_keys[0].ondelete == "CASCADE"


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
