"""
Abstract: Local fixture loader for taxonomy card-scope layout tuning.
Out of scope: HTTP transport behavior and production taxonomy persistence.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from modules.taxonomy.dto import (
    TaxonomyCardScopeLayout,
    TaxonomyCardScopeLayoutEdge,
    TaxonomyCardScopeLayoutNode,
)
from modules.taxonomy.layout import TaxonomyCardScopeLayoutParams, build_card_scope_layout

DEFAULT_LAYOUT_LAB_FIXTURE = "obsidian-sample"
_FIXTURE_DIRECTORY = Path(__file__).with_name("layout_lab_fixtures")


class LayoutLabFixtureNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class LayoutLabFixtureSummary:
    name: str
    node_count: int
    edge_count: int


@dataclass(frozen=True)
class _LayoutLabFixture:
    name: str
    generated_at: datetime
    nodes: list[TaxonomyCardScopeLayoutNode]
    edges: list[TaxonomyCardScopeLayoutEdge]


def list_layout_lab_fixtures() -> list[LayoutLabFixtureSummary]:
    return [
        LayoutLabFixtureSummary(
            name=fixture.name,
            node_count=len(fixture.nodes),
            edge_count=len(fixture.edges),
        )
        for fixture in _load_layout_lab_fixtures()
    ]


def solve_layout_lab_fixture(
    *,
    fixture_name: str,
    params: TaxonomyCardScopeLayoutParams,
) -> TaxonomyCardScopeLayout:
    fixture = _load_layout_lab_fixture(fixture_name)
    return build_card_scope_layout(
        nodes=fixture.nodes,
        edges=fixture.edges,
        generated_at=fixture.generated_at,
        params=params,
    )


def _load_layout_lab_fixture(fixture_name: str) -> _LayoutLabFixture:
    for fixture in _load_layout_lab_fixtures():
        if fixture.name == fixture_name:
            return fixture
    raise LayoutLabFixtureNotFoundError(f"Layout lab fixture {fixture_name!r} was not found.")


def _load_layout_lab_fixtures() -> list[_LayoutLabFixture]:
    return [
        _load_layout_lab_fixture_path(path) for path in sorted(_FIXTURE_DIRECTORY.glob("*.json"))
    ]


def _load_layout_lab_fixture_path(path: Path) -> _LayoutLabFixture:
    raw = _as_mapping(json.loads(path.read_text(encoding="utf-8")), field_name="fixture")
    return _LayoutLabFixture(
        name=str(raw["name"]),
        generated_at=datetime.fromisoformat(str(raw["generated_at"])),
        nodes=_parse_fixture_nodes(raw["nodes"]),
        edges=[
            TaxonomyCardScopeLayoutEdge.model_validate(edge)
            for edge in _as_list(raw["edges"], field_name="edges")
        ],
    )


def _parse_fixture_nodes(raw_nodes: object) -> list[TaxonomyCardScopeLayoutNode]:
    nodes: list[TaxonomyCardScopeLayoutNode] = []
    for raw_node in _as_list(raw_nodes, field_name="nodes"):
        node = _as_mapping(raw_node, field_name="node")
        node_id = node["id"]
        scope = node["scope"]
        if not isinstance(node_id, int):
            raise ValueError("Fixture node id must be an integer.")
        if scope not in {"inner", "outer"}:
            raise ValueError("Fixture node scope must be inner or outer.")
        nodes.append(
            TaxonomyCardScopeLayoutNode(
                id=node_id,
                scope=cast(Literal["inner", "outer"], scope),
                x=0.0,
                y=0.0,
            )
        )
    return nodes


def _as_mapping(value: object, *, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Fixture field {field_name!r} must be an object.")
    return cast(Mapping[str, object], value)


def _as_list(value: object, *, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"Fixture field {field_name!r} must be a list.")
    return cast(list[object], value)
