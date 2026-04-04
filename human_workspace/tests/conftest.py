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


def _write_bz2_index(input_dir: Path, file_name: str, page_titles: list[str]) -> Path:
    index_path = input_dir / file_name
    index_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{offset}:{1000 + offset}:{title}"
        for offset, title in enumerate(page_titles)
    ]
    index_path.write_bytes(bz2.compress("\n".join(lines).encode("utf-8")))
    return index_path


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


@pytest.fixture
def sample_input_dir_with_indexes_and_repeated_stream_number(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input-with-indexes"
    first_xml = """
<mediawiki>
  <page>
    <title>Alpha Article</title>
    <ns>0</ns>
    <id>200</id>
    <revision>
      <id>2000</id>
      <timestamp>2026-03-01T01:00:00Z</timestamp>
      <text xml:space="preserve">Alpha lead sentence.</text>
    </revision>
  </page>
  <page>
    <title>Alpha Redirect</title>
    <ns>0</ns>
    <id>201</id>
    <redirect title="Alpha Target" />
    <revision>
      <id>2001</id>
      <timestamp>2026-03-01T01:01:00Z</timestamp>
      <text xml:space="preserve">#REDIRECT [[Alpha Target]]</text>
    </revision>
  </page>
  <page>
    <title>Alpha Topic (disambiguation)</title>
    <ns>0</ns>
    <id>202</id>
    <revision>
      <id>2002</id>
      <timestamp>2026-03-01T01:02:00Z</timestamp>
      <text xml:space="preserve">{{disambiguation}}</text>
    </revision>
  </page>
</mediawiki>
""".strip()
    second_xml = """
<mediawiki>
  <page>
    <title>Beta Article</title>
    <ns>0</ns>
    <id>300</id>
    <revision>
      <id>3000</id>
      <timestamp>2026-03-01T02:00:00Z</timestamp>
      <text xml:space="preserve">Beta lead sentence.</text>
    </revision>
  </page>
  <page>
    <title>Beta Redirect</title>
    <ns>0</ns>
    <id>301</id>
    <revision>
      <id>3001</id>
      <timestamp>2026-03-01T02:01:00Z</timestamp>
      <text xml:space="preserve">#REDIRECT [[Beta Target]]</text>
    </revision>
  </page>
  <page>
    <title>Talk:Beta Article</title>
    <ns>1</ns>
    <id>302</id>
    <revision>
      <id>3002</id>
      <timestamp>2026-03-01T02:02:00Z</timestamp>
      <text xml:space="preserve">Talk page.</text>
    </revision>
  </page>
</mediawiki>
""".strip()

    _write_bz2_split(
        input_dir,
        "enwiki-20260301-pages-articles-multistream15.xml-p17324603p17460152.bz2",
        first_xml,
    )
    _write_bz2_index(
        input_dir,
        "enwiki-20260301-pages-articles-multistream-index15.txt-p17324603p17460152.bz2",
        ["Alpha Article", "Alpha Redirect", "Alpha Topic (disambiguation)"],
    )
    _write_bz2_split(
        input_dir,
        "enwiki-20260301-pages-articles-multistream15.xml-p17460153p17560152.bz2",
        second_xml,
    )
    _write_bz2_index(
        input_dir,
        "enwiki-20260301-pages-articles-multistream-index15.txt-p17460153p17560152.bz2",
        ["Beta Article", "Beta Redirect", "Talk:Beta Article"],
    )
    return input_dir


@pytest.fixture
def sample_input_dir_with_parallel_broken_pages(tmp_path: Path) -> Path:
    input_dir = tmp_path / "input-with-parallel-broken-pages"
    first_xml = """
<mediawiki>
  <page>
    <title>Broken Alpha</title>
    <ns>0</ns>
    <id>400</id>
    <revision>
      <id>4000</id>
      <timestamp>2026-03-01T03:00:00Z</timestamp>
      <text xml:space="preserve">{{Infobox scientist}}&lt;ref&gt;citation&lt;/ref&gt;</text>
    </revision>
  </page>
</mediawiki>
""".strip()
    second_xml = """
<mediawiki>
  <page>
    <title>Broken Beta</title>
    <ns>0</ns>
    <id>500</id>
    <revision>
      <id>5000</id>
      <timestamp>2026-03-01T04:00:00Z</timestamp>
      <text xml:space="preserve">{{Infobox scientist}}&lt;ref&gt;citation&lt;/ref&gt;</text>
    </revision>
  </page>
</mediawiki>
""".strip()

    _write_bz2_split(
        input_dir,
        "enwiki-20260301-pages-articles-multistream17.xml-p20570393p20600000.bz2",
        first_xml,
    )
    _write_bz2_index(
        input_dir,
        "enwiki-20260301-pages-articles-multistream-index17.txt-p20570393p20600000.bz2",
        ["Broken Alpha"],
    )
    _write_bz2_split(
        input_dir,
        "enwiki-20260301-pages-articles-multistream18.xml-p20600001p20650000.bz2",
        second_xml,
    )
    _write_bz2_index(
        input_dir,
        "enwiki-20260301-pages-articles-multistream-index18.txt-p20600001p20650000.bz2",
        ["Broken Beta"],
    )
    return input_dir
