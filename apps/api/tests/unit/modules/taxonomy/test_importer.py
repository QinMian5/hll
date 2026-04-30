"""
Abstract: Unit tests for taxonomy YAML parsing and bootstrap import semantics.
Out of scope: Database trigger enforcement and runtime script invocation.
"""

from __future__ import annotations

import pytest

from modules.taxonomy.dto import TaxonomyImportNode
from modules.taxonomy.errors import TaxonomyImportError
from modules.taxonomy.importer import TaxonomyImporter, parse_taxonomy_yaml
from modules.taxonomy.route_path import slugify_taxonomy_route_segment

_SAMPLE_LCC_YAML = """
Science:
  - Mathematics:
      - General
      - Algebra
  - Physics
"""


class _FakeImportRepo:
    def __init__(self) -> None:
        self.next_id = 1
        self.created_nodes: list[dict[str, object]] = []
        self.committed = False
        self.rolled_back = False

    async def has_any_taxonomy_nodes(self) -> bool:
        return False

    async def create_taxonomy_node(
        self,
        *,
        parent_id: int | None,
        name: str,
        depth: int,
        is_leaf: bool,
    ) -> int:
        node_id = self.next_id
        self.next_id += 1
        self.created_nodes.append(
            {
                "id": node_id,
                "parent_id": parent_id,
                "name": name,
                "depth": depth,
                "is_leaf": is_leaf,
            }
        )
        return node_id

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def test_slugify_taxonomy_route_segment_uses_readable_lcc_segments() -> None:
    assert (
        slugify_taxonomy_route_segment("Electronic computers. Computer science")
        == "electronic-computers-computer-science"
    )
    assert slugify_taxonomy_route_segment("Science (General)") == "science-general"


def test_parse_taxonomy_yaml_builds_depth_parent_path_and_leaf_flags() -> None:
    nodes = parse_taxonomy_yaml(_SAMPLE_LCC_YAML)

    assert nodes == [
        TaxonomyImportNode(
            path=("Science",),
            parent_path=None,
            name="Science",
            depth=0,
            is_leaf=False,
        ),
        TaxonomyImportNode(
            path=("Science", "Mathematics"),
            parent_path=("Science",),
            name="Mathematics",
            depth=1,
            is_leaf=False,
        ),
        TaxonomyImportNode(
            path=("Science", "Mathematics", "General"),
            parent_path=("Science", "Mathematics"),
            name="General",
            depth=2,
            is_leaf=True,
        ),
        TaxonomyImportNode(
            path=("Science", "Mathematics", "Algebra"),
            parent_path=("Science", "Mathematics"),
            name="Algebra",
            depth=2,
            is_leaf=True,
        ),
        TaxonomyImportNode(
            path=("Science", "Physics"),
            parent_path=("Science",),
            name="Physics",
            depth=1,
            is_leaf=True,
        ),
    ]


def test_parse_taxonomy_yaml_rejects_unsupported_root_shape() -> None:
    with pytest.raises(TaxonomyImportError, match="root taxonomy document must be a mapping"):
        parse_taxonomy_yaml("- Science")


@pytest.mark.anyio
async def test_import_yaml_rejects_sibling_route_slug_collisions() -> None:
    repo = _FakeImportRepo()
    importer = TaxonomyImporter(repo=repo)

    with pytest.raises(TaxonomyImportError, match="duplicate route slug"):
        await importer.import_yaml_text(
            """
Science:
  - Science General
  - Science-General
"""
        )

    assert repo.created_nodes == []
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_import_yaml_rejects_names_that_cannot_form_route_slugs() -> None:
    repo = _FakeImportRepo()
    importer = TaxonomyImporter(repo=repo)

    with pytest.raises(TaxonomyImportError, match="ASCII letter or digit"):
        await importer.import_yaml_text(
            """
"!!!": null
"""
        )

    assert repo.created_nodes == []
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_import_yaml_rejects_user_nodes_colliding_with_system_unclassified_slug() -> None:
    repo = _FakeImportRepo()
    importer = TaxonomyImporter(repo=repo)

    with pytest.raises(TaxonomyImportError, match="duplicate route slug"):
        await importer.import_yaml_text(
            """
Unclassified: null
"""
        )

    assert repo.created_nodes == []
    assert repo.rolled_back is False
