"""
Abstract: Bootstrap-only taxonomy import orchestration from YAML into persisted tree rows.
Out of scope: Final assignment workflows and taxonomy view rendering behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from modules.taxonomy.dto import TaxonomyImportNode
from modules.taxonomy.errors import TaxonomyImportError
from modules.taxonomy.ports import TaxonomyImportPort
from modules.taxonomy.repo import ROOT_NODE_NAME, UNCLASSIFIED_NODE_NAME
from modules.taxonomy.route_path import slugify_taxonomy_route_segment

TaxonomyYamlMapping = Mapping[str, Any]


class TaxonomyImporter:
    def __init__(self, *, repo: TaxonomyImportPort) -> None:
        self._repo = repo

    async def import_yaml_text(self, yaml_text: str) -> int:
        if await self._repo.has_any_taxonomy_nodes():
            raise TaxonomyImportError("taxonomy store already contains rows")

        nodes = parse_taxonomy_yaml(yaml_text)
        _validate_route_slugs(nodes)
        path_to_id: dict[tuple[str, ...], int] = {}
        imported_count = 0

        try:
            root_id = await self._repo.create_taxonomy_node(
                parent_id=None,
                name=ROOT_NODE_NAME,
                depth=0,
                is_leaf=False,
            )
            imported_count += 1
            await self._repo.create_taxonomy_node(
                parent_id=root_id,
                name=UNCLASSIFIED_NODE_NAME,
                depth=1,
                is_leaf=True,
            )
            imported_count += 1
            for node in nodes:
                parent_id = root_id if node.parent_path is None else path_to_id[node.parent_path]
                node_id = await self._repo.create_taxonomy_node(
                    parent_id=parent_id,
                    name=node.name,
                    depth=node.depth + 1,
                    is_leaf=False,
                )
                imported_count += 1
                await self._repo.create_taxonomy_node(
                    parent_id=node_id,
                    name=UNCLASSIFIED_NODE_NAME,
                    depth=node.depth + 2,
                    is_leaf=True,
                )
                imported_count += 1
                path_to_id[node.path] = node_id
            await self._repo.commit()
        except Exception:
            await self._repo.rollback()
            raise

        return imported_count

    async def import_yaml_file(self, yaml_path: Path) -> int:
        return await self.import_yaml_text(yaml_path.read_text(encoding="utf-8"))


def parse_taxonomy_yaml(yaml_text: str) -> list[TaxonomyImportNode]:
    document = yaml.safe_load(yaml_text)
    if not isinstance(document, Mapping):
        raise TaxonomyImportError("root taxonomy document must be a mapping")

    nodes: list[TaxonomyImportNode] = []
    _extend_mapping_nodes(
        mapping=_normalize_yaml_mapping(document),
        parent_path=None,
        depth=0,
        nodes=nodes,
    )
    return nodes


def _extend_mapping_nodes(
    *,
    mapping: TaxonomyYamlMapping,
    parent_path: tuple[str, ...] | None,
    depth: int,
    nodes: list[TaxonomyImportNode],
) -> None:
    for raw_name, raw_children in mapping.items():
        name = _coerce_node_name(raw_name)
        path = (name,) if parent_path is None else (*parent_path, name)
        is_leaf = _children_spec_is_leaf(raw_children)
        nodes.append(
            TaxonomyImportNode(
                path=path,
                parent_path=parent_path,
                name=name,
                depth=depth,
                is_leaf=is_leaf,
            )
        )
        _extend_child_nodes(
            spec=raw_children,
            parent_path=path,
            depth=depth + 1,
            nodes=nodes,
        )


def _extend_child_nodes(
    *,
    spec: object,
    parent_path: tuple[str, ...],
    depth: int,
    nodes: list[TaxonomyImportNode],
) -> None:
    if spec is None:
        return
    if isinstance(spec, str):
        nodes.append(
            TaxonomyImportNode(
                path=(*parent_path, spec),
                parent_path=parent_path,
                name=spec,
                depth=depth,
                is_leaf=True,
            )
        )
        return
    if isinstance(spec, Mapping):
        _extend_mapping_nodes(
            mapping=_normalize_yaml_mapping(spec),
            parent_path=parent_path,
            depth=depth,
            nodes=nodes,
        )
        return
    if isinstance(spec, Sequence) and not isinstance(spec, str):
        for item in spec:
            if isinstance(item, str):
                nodes.append(
                    TaxonomyImportNode(
                        path=(*parent_path, item),
                        parent_path=parent_path,
                        name=item,
                        depth=depth,
                        is_leaf=True,
                    )
                )
                continue
            if isinstance(item, Mapping):
                _extend_mapping_nodes(
                    mapping=_normalize_yaml_mapping(item),
                    parent_path=parent_path,
                    depth=depth,
                    nodes=nodes,
                )
                continue
            raise TaxonomyImportError("taxonomy child list items must be strings or mappings")
        return
    raise TaxonomyImportError("taxonomy node children must be a mapping, list, string, or null")


def _children_spec_is_leaf(spec: object) -> bool:
    if spec is None:
        return True
    if isinstance(spec, str):
        return False
    if isinstance(spec, Mapping):
        return len(spec) == 0
    if isinstance(spec, Sequence) and not isinstance(spec, str):
        return len(spec) == 0
    raise TaxonomyImportError("taxonomy node children must be a mapping, list, string, or null")


def _validate_route_slugs(nodes: list[TaxonomyImportNode]) -> None:
    slugs_by_parent: dict[tuple[str, ...] | None, dict[str, str]] = {}

    def add_slug(*, parent_path: tuple[str, ...] | None, name: str) -> None:
        try:
            route_slug = slugify_taxonomy_route_segment(name)
        except ValueError as error:
            raise TaxonomyImportError(str(error)) from error

        siblings = slugs_by_parent.setdefault(parent_path, {})
        previous = siblings.get(route_slug)
        if previous is not None:
            raise TaxonomyImportError(
                f"taxonomy sibling names produce duplicate route slug {route_slug!r}"
            )
        siblings[route_slug] = name

    add_slug(parent_path=None, name=UNCLASSIFIED_NODE_NAME)
    for node in nodes:
        add_slug(parent_path=node.parent_path, name=node.name)
        add_slug(parent_path=node.path, name=UNCLASSIFIED_NODE_NAME)


def _normalize_yaml_mapping(spec: Mapping[Any, Any]) -> TaxonomyYamlMapping:
    mapping: dict[str, Any] = {}
    for key, value in spec.items():
        if not isinstance(key, str):
            raise TaxonomyImportError("taxonomy node names must be strings")
        mapping[key] = value
    return mapping


def _coerce_node_name(raw_name: object) -> str:
    if not isinstance(raw_name, str):
        raise TaxonomyImportError("taxonomy node names must be strings")
    name = raw_name.strip()
    if not name:
        raise TaxonomyImportError("taxonomy node names must be non-empty")
    return name
