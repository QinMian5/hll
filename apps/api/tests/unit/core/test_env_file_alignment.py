"""
Abstract: Unit tests enforcing structural alignment of tracked env template files.
Out of scope: Secret value validation and runtime settings loading behavior.
"""

from __future__ import annotations

from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parents[5] / "infra" / "env" / ".env.example"


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
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    assert lines, f"{ENV_EXAMPLE} must not be empty."

    seen_keys: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        kind = _line_kind(line)
        if kind != "key_value":
            continue

        key = _parse_env_key(path=ENV_EXAMPLE, line_number=line_number, line=line)
        assert key not in seen_keys, f"{ENV_EXAMPLE}:{line_number} repeats key '{key}'."
        seen_keys.add(key)
