"""
Abstract: Unit tests for taxonomy YAML parsing and bootstrap import semantics.
Out of scope: Database trigger enforcement and runtime script invocation.
"""

from __future__ import annotations

import pytest

from modules.taxonomy.dto import TaxonomyImportNode
from modules.taxonomy.errors import TaxonomyImportError
from modules.taxonomy.importer import parse_taxonomy_yaml

_SAMPLE_LCC_YAML = """
Science:
  - Mathematics:
      - General
      - Algebra
  - Physics
"""


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
