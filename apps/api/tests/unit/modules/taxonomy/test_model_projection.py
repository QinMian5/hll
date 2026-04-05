"""
Abstract: Unit tests for taxonomy persistence schema projection.
Out of scope: Migration execution and runtime database I/O behavior.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Table, UniqueConstraint

from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode
from shared.db.base import Base


def test_projection_registers_required_tables() -> None:
    table_names = set(Base.metadata.tables)
    assert {"taxonomy_nodes", "node_taxonomy_assignments"} <= table_names


def test_taxonomy_nodes_projection_contains_parent_depth_and_leaf_flag() -> None:
    table = cast(Table, TaxonomyNode.__table__)

    assert table.c.parent_id.nullable is True
    assert table.c.depth.nullable is False
    assert table.c.is_leaf.nullable is False


def test_node_taxonomy_assignments_projection_contains_unique_node_constraint() -> None:
    table = cast(Table, NodeTaxonomyAssignment.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]

    assert {"node_id"} in unique_column_sets
