"""
Abstract: Static boundary tests for source-pipeline architecture constraints.
Out of scope: Runtime integration behavior and API module boundary checks.
"""

from __future__ import annotations

from pathlib import Path

SOURCE_PIPELINE_SRC = Path(__file__).resolve().parents[2] / "src" / "source_pipeline"


def _python_sources() -> list[Path]:
    return sorted(SOURCE_PIPELINE_SRC.rglob("*.py"))


def test_source_pipeline_does_not_import_api_internal_modules() -> None:
    forbidden_fragments = (
        "from core",
        "import core",
        "from modules.",
        "import modules.",
        "from entrypoints.",
        "import entrypoints.",
        "apps.api",
    )

    violations: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in text:
                violations.append(f"{path.relative_to(SOURCE_PIPELINE_SRC)}: {fragment}")

    assert violations == []


def test_source_pipeline_does_not_write_knowledge_graph_tables_directly() -> None:
    forbidden_fragments = (
        "knowledge_graph",
        "INSERT INTO nodes",
        "INSERT INTO edges",
        "UPDATE nodes",
        "UPDATE edges",
        "DELETE FROM nodes",
        "DELETE FROM edges",
    )

    violations: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            if fragment in text:
                violations.append(f"{path.relative_to(SOURCE_PIPELINE_SRC)}: {fragment}")

    assert violations == []
