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


def _write_bz2_split(input_dir: Path, file_name: str, xml_text: str) -> Path:
    split_path = input_dir / file_name
    split_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.write_bytes(bz2.compress(xml_text.encode("utf-8")))
    return split_path


@pytest.fixture
def sample_input_dir(sample_pages_xml_path: Path, tmp_path: Path) -> Path:
    input_dir = tmp_path / "input"
    _write_bz2_split(
        input_dir,
        "pages-articles-multistream-00001.xml-00000.bz2",
        sample_pages_xml_path.read_text(encoding="utf-8"),
    )
    return input_dir


@pytest.fixture
def sample_input_dir_with_one_broken_page(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input-with-broken-page"
    _write_bz2_split(
        input_dir,
        "pages-articles-multistream-00001.xml-00000.bz2",
        """
<mediawiki>
  <page>
    <title>Alan Turing</title>
    <ns>0</ns>
    <id>100</id>
    <revision>
      <id>1000</id>
      <timestamp>2026-03-01T00:00:00Z</timestamp>
      <text xml:space="preserve">Lead sentence.</text>
    </revision>
  </page>
  <page>
    <title>Broken Page</title>
    <ns>0</ns>
    <id>101</id>
    <revision>
      <id>1001</id>
      <timestamp>2026-03-01T00:01:00Z</timestamp>
      <text xml:space="preserve">{{Infobox scientist}}&lt;ref&gt;citation&lt;/ref&gt;</text>
    </revision>
  </page>
</mediawiki>
""".strip(),
    )
    return input_dir
