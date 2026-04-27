"""
Abstract: Architecture boundary tests for the public Knowledge MCP service.
Out of scope: Runtime MCP protocol behavior and deployment configuration rendering.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
MCP_SRC = REPO_ROOT / "apps" / "mcp" / "src"
INTERNAL_API_ADAPTER = MCP_SRC / "knowledge_mcp" / "internal_api"
FORBIDDEN_IMPORT_ROOTS = ("apps", "core", "entrypoints", "modules", "shared")


def _python_files() -> list[Path]:
    return sorted(MCP_SRC.rglob("*.py"))


def _module_root(import_name: str) -> str:
    return import_name.split(".", 1)[0]


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    return imports


def test_mcp_source_does_not_import_backend_internals() -> None:
    violations: list[str] = []
    for path in _python_files():
        for module in _imported_modules(path):
            if _module_root(module) in FORBIDDEN_IMPORT_ROOTS:
                violations.append(f"{path.relative_to(REPO_ROOT)} imports {module}")

    assert violations == []


def test_mcp_source_does_not_reference_api_source_path() -> None:
    violations = [
        str(path.relative_to(REPO_ROOT))
        for path in _python_files()
        if "apps/api/src" in path.read_text(encoding="utf-8")
    ]

    assert violations == []


def test_generated_contract_client_imports_are_isolated_to_internal_api_adapter() -> None:
    violations: list[str] = []
    for path in _python_files():
        imports = _imported_modules(path)
        if not any(module.startswith("knowledge_contracts_client") for module in imports):
            continue
        if INTERNAL_API_ADAPTER not in path.parents:
            violations.append(str(path.relative_to(REPO_ROOT)))

    assert violations == []
