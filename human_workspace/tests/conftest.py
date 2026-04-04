"""
Abstract: Shared pytest fixtures for sample Wikipedia preprocessing inputs.
Out of scope: Pipeline orchestration assertions and production XML parsing logic.
"""

from __future__ import annotations

import bz2
from pathlib import Path

import pytest


@pytest.fixture
def sample_pages_xml_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_pages.xml"


@pytest.fixture
def sample_bz2_split(sample_pages_xml_path: Path, tmp_path: Path) -> Path:
    split_path = tmp_path / "pages-articles-multistream-00001.xml-00000.bz2"
    split_path.write_bytes(bz2.compress(sample_pages_xml_path.read_bytes()))
    return split_path
