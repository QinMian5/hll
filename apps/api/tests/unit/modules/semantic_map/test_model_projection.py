"""
Abstract: Unit tests for semantic-map snapshot persistence schema projection.
Out of scope: Migration execution and runtime database I/O behavior.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import PrimaryKeyConstraint, Table, UniqueConstraint

from modules.semantic_map.model import SemanticMapRegionTile, SemanticMapSnapshot
from shared.db.base import Base


def test_projection_registers_required_tables() -> None:
    table_names = set(Base.metadata.tables)
    assert {"semantic_map_snapshots", "semantic_map_region_tiles"} <= table_names


def test_snapshot_manifest_model_contains_id_and_bounds() -> None:
    table = cast(Table, SemanticMapSnapshot.__table__)

    assert table.c.id.nullable is False
    assert table.c.version.nullable is False
    assert table.c.schema_version.nullable is False
    assert table.c.world_bounds.nullable is False
    assert table.c.tile_size.nullable is False
    assert table.c.max_zoom.nullable is False
    assert table.c.default_view.nullable is False
    assert table.c.default_semantic_level.nullable is False
    assert table.c.current.nullable is False


def test_snapshot_projection_keeps_unique_external_version_key() -> None:
    table = cast(Table, SemanticMapSnapshot.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]

    assert {"version"} in unique_column_sets


def test_region_tile_projection_uses_integer_primary_key() -> None:
    table = cast(Table, SemanticMapRegionTile.__table__)
    primary_key = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, PrimaryKeyConstraint)
    )
    pk_column_names = {column.name for column in primary_key.columns}

    assert pk_column_names == {"id"}


def test_region_tile_projection_keeps_unique_snapshot_tile_lookup_key() -> None:
    table = cast(Table, SemanticMapRegionTile.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]
    unique_column_sets = [
        {column.name for column in constraint.columns} for constraint in unique_constraints
    ]

    assert {
        "snapshot_id",
        "semantic_level",
        "tile_z",
        "tile_x",
        "tile_y",
    } in unique_column_sets


def test_region_tile_payload_columns_are_required() -> None:
    table = cast(Table, SemanticMapRegionTile.__table__)

    assert table.c.snapshot_id.nullable is False
    assert table.c.tile_bounds.nullable is False
    assert table.c.region_count.nullable is False
    assert table.c.label_count.nullable is False
    assert table.c.regions.nullable is False
    assert table.c.labels.nullable is False
