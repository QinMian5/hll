"""
Abstract: Unit tests for the local taxonomy layout tuning fixture boundary.
Out of scope: HTTP transport behavior and production taxonomy persistence.
"""

from __future__ import annotations

import pytest

from modules.taxonomy.layout import TaxonomyCardScopeLayoutParams
from modules.taxonomy.layout_lab import (
    DEFAULT_LAYOUT_LAB_FIXTURE,
    LayoutLabFixtureNotFoundError,
    list_layout_lab_fixtures,
    solve_layout_lab_fixture,
)


def test_list_layout_lab_fixtures_reports_local_sample_data() -> None:
    fixtures = list_layout_lab_fixtures()

    assert [fixture.name for fixture in fixtures] == [
        DEFAULT_LAYOUT_LAB_FIXTURE,
        "obsidian-sample",
    ]
    assert fixtures[0].node_count == 1233
    assert fixtures[0].edge_count == 2158
    assert fixtures[1].node_count == 16
    assert fixtures[1].edge_count == 18


def test_solve_layout_lab_fixture_uses_production_layout_builder() -> None:
    compact = solve_layout_lab_fixture(
        fixture_name="obsidian-sample",
        params=TaxonomyCardScopeLayoutParams(
            seed_base_radius=40.0,
            seed_radius_step=10.0,
            simulation_ticks=0,
        ),
    )
    expanded = solve_layout_lab_fixture(
        fixture_name="obsidian-sample",
        params=TaxonomyCardScopeLayoutParams(
            seed_base_radius=120.0,
            seed_radius_step=30.0,
            simulation_ticks=0,
        ),
    )

    assert compact.layout_version == "taxonomy-card-scope-layout-v1"
    assert compact.node_count == 16
    assert compact.edge_count == 18
    assert compact.nodes[0].x == 50.0
    assert expanded.nodes[0].x == 150.0


def test_solve_layout_lab_fixture_loads_prod_heat_thermodynamics_scope() -> None:
    layout = solve_layout_lab_fixture(
        fixture_name=DEFAULT_LAYOUT_LAB_FIXTURE,
        params=TaxonomyCardScopeLayoutParams(simulation_ticks=0),
    )

    assert DEFAULT_LAYOUT_LAB_FIXTURE == "prod-heat-thermodynamics"
    assert layout.node_count == 1233
    assert layout.edge_count == 2158
    assert {node.scope for node in layout.nodes} == {"inner", "outer"}


def test_solve_layout_lab_fixture_rejects_unknown_fixture() -> None:
    with pytest.raises(LayoutLabFixtureNotFoundError, match="missing"):
        solve_layout_lab_fixture(
            fixture_name="missing",
            params=TaxonomyCardScopeLayoutParams(),
        )
