"""
Abstract: Unit tests for taxonomy persistence schema projection.
Out of scope: Migration execution and runtime database I/O behavior.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import CheckConstraint, Index, Table, UniqueConstraint

from modules.taxonomy.model import (
    NodeTaxonomyAssignment,
    TaxonomyCardScopeLayout,
    TaxonomyCardScopeLayoutComputeRequest,
    TaxonomyNode,
    TaxonomyScopeProjectionEdge,
)
from shared.db.base import Base


def test_projection_registers_required_tables() -> None:
    table_names = set(Base.metadata.tables)
    assert {
        "taxonomy_nodes",
        "node_taxonomy_assignments",
        "taxonomy_scope_projection_edges",
        "taxonomy_card_scope_layouts",
        "taxonomy_card_scope_layout_compute_requests",
    } <= table_names


def test_taxonomy_nodes_projection_contains_parent_and_depth_without_leaf_flag() -> None:
    table = cast(Table, TaxonomyNode.__table__)

    assert table.c.parent_id.nullable is True
    assert table.c.depth.nullable is False
    assert "is_leaf" not in table.c


def test_taxonomy_nodes_projection_contains_route_slug_contract() -> None:
    table = cast(Table, TaxonomyNode.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    check_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, CheckConstraint)
    ]

    assert "route_slug" in table.c
    assert table.c.route_slug.nullable is False
    assert any(
        constraint.name == "uq_taxonomy_nodes_parent_route_slug"
        and [column.name for column in constraint.columns] == ["parent_id", "route_slug"]
        for constraint in unique_constraints
    )
    assert any(
        constraint.name == "ck_taxonomy_nodes_route_slug_non_empty"
        for constraint in check_constraints
    )


def test_taxonomy_nodes_projection_contains_single_root_partial_index() -> None:
    table = cast(Table, TaxonomyNode.__table__)
    indexes = [constraint for constraint in table.indexes if isinstance(constraint, Index)]
    root_indexes = [index for index in indexes if index.name == "uq_taxonomy_nodes_single_root"]

    assert root_indexes
    assert root_indexes[0].unique is True
    assert str(root_indexes[0].dialect_options["postgresql"]["where"]) == "parent_id IS NULL"


def test_taxonomy_nodes_projection_contains_case_insensitive_sibling_name_index() -> None:
    table = cast(Table, TaxonomyNode.__table__)
    indexes = [constraint for constraint in table.indexes if isinstance(constraint, Index)]
    sibling_indexes = [
        index for index in indexes if index.name == "uq_taxonomy_nodes_parent_lower_name"
    ]

    assert sibling_indexes
    assert sibling_indexes[0].unique is True
    assert str(sibling_indexes[0].dialect_options["postgresql"]["where"]) == (
        "parent_id IS NOT NULL"
    )
    assert "lower(name)" in str(sibling_indexes[0].expressions[1])


def test_node_taxonomy_assignments_projection_contains_unique_node_constraint() -> None:
    table = cast(Table, NodeTaxonomyAssignment.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]

    assert {"node_id"} in unique_column_sets


def test_node_taxonomy_assignments_projection_contains_scope_lookup_indexes() -> None:
    table = cast(Table, NodeTaxonomyAssignment.__table__)
    indexes = [constraint for constraint in table.indexes if isinstance(constraint, Index)]
    index_column_sets = [{column.name for column in index.columns} for index in indexes]

    assert {"taxonomy_node_id"} in index_column_sets
    assert {"taxonomy_node_id", "node_id"} in index_column_sets


def test_taxonomy_scope_projection_edges_projection_contains_required_keys_and_indexes() -> None:
    table = cast(Table, TaxonomyScopeProjectionEdge.__table__)
    indexes = [constraint for constraint in table.indexes if isinstance(constraint, Index)]
    index_column_sets = [{column.name for column in index.columns} for index in indexes]

    assert [column.name for column in table.primary_key.columns] == [
        "scope_kind",
        "taxonomy_node_id",
        "edge_id",
    ]
    assert {"edge_id"} in index_column_sets
    assert {"scope_kind", "taxonomy_node_id"} in index_column_sets


def test_taxonomy_card_scope_layout_projection_contains_durable_read_model_key() -> None:
    table = cast(Table, TaxonomyCardScopeLayout.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    indexes = [constraint for constraint in table.indexes if isinstance(constraint, Index)]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]
    index_column_sets = [{column.name for column in index.columns} for index in indexes]

    assert {"scope_kind", "taxonomy_node_id", "layout_version"} in unique_column_sets
    assert table.c.input_fingerprint.nullable is False
    assert table.c.layout_payload.nullable is False
    assert {"scope_kind", "taxonomy_node_id"} in index_column_sets
    assert {"input_fingerprint"} in index_column_sets


def test_taxonomy_card_scope_layout_compute_requests_projection_contains_singleflight_key() -> None:
    table = cast(Table, TaxonomyCardScopeLayoutComputeRequest.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    indexes = [constraint for constraint in table.indexes if isinstance(constraint, Index)]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]
    index_column_sets = [{column.name for column in index.columns} for index in indexes]

    assert {"scope_kind", "taxonomy_node_id", "layout_version"} in unique_column_sets
    assert table.c.input_fingerprint.nullable is False
    assert table.c.status.nullable is False
    assert table.c.attempt_count.nullable is False
    assert {"status", "requested_at"} in index_column_sets
    assert {"scope_kind", "taxonomy_node_id"} in index_column_sets
