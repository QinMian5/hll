"""
Abstract: Unit tests enforcing structural alignment of tracked env template files.
Out of scope: Secret value validation and runtime settings loading behavior.
"""

from __future__ import annotations

from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parents[5] / "infra" / "env" / ".env.example"
LOCAL_ENV_FILES = (".env.dev", ".env.prod", ".env.test")


def _line_kind(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return "blank"
    if stripped.startswith("#"):
        return "comment"
    return "key_value"


def _parse_env_key(*, path: Path, line_number: int, line: str) -> str:
    if "=" not in line:
        raise AssertionError(f"{path}:{line_number} must contain '=' for env key-value structure.")

    key, _ = line.split("=", 1)
    key = key.strip()
    if not key:
        raise AssertionError(f"{path}:{line_number} has an empty key before '='.")

    return key


def test_tracked_env_example_has_valid_line_structure_and_unique_keys() -> None:
    _parse_env_keys(ENV_EXAMPLE)


def test_tracked_env_example_contains_api_cache_ttl_keys() -> None:
    keys = _parse_env_keys(ENV_EXAMPLE)
    for key in (
        "KNOWLEDGE_API_SEARCH_RESPONSE_CACHE_TTL_SECONDS",
        "KNOWLEDGE_API_SEARCH_EMBEDDING_CACHE_TTL_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS",
        "KNOWLEDGE_API_TAXONOMY_LEAF_LAYOUT_CACHE_TTL_SECONDS",
    ):
        assert key in keys


def _parse_env_keys(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines, f"{path} must not be empty."

    keys: list[str] = []
    seen_keys: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        kind = _line_kind(line)
        if kind != "key_value":
            continue

        key = _parse_env_key(path=path, line_number=line_number, line=line)
        assert key not in seen_keys, f"{path}:{line_number} repeats key '{key}'."
        keys.append(key)
        seen_keys.add(key)

    return keys


def test_local_env_files_match_example_key_set_and_order() -> None:
    expected_keys = _parse_env_keys(ENV_EXAMPLE)

    for filename in LOCAL_ENV_FILES:
        local_env_file = ENV_EXAMPLE.parent / filename
        if not local_env_file.exists():
            continue

        actual_keys = _parse_env_keys(local_env_file)
        assert actual_keys == expected_keys, (
            f"{local_env_file} must preserve the same env keys and key order as {ENV_EXAMPLE}.\n"
            f"expected: {expected_keys}\n"
            f"actual:   {actual_keys}"
        )
