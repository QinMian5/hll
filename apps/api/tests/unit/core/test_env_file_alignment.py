"""
Abstract: Unit tests enforcing structural alignment of tracked env template files.
Out of scope: Secret value validation and runtime settings loading behavior.
"""

from __future__ import annotations

from pathlib import Path

ENV_FILENAMES = (".env.example", ".env.dev", ".env.prod", ".env.test")


def _line_kind(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return "blank"
    if stripped.startswith("#"):
        return "comment"
    return "key_value"


def _parse_env_key(*, path: Path, line_number: int, line: str) -> str:
    if "=" not in line:
        raise AssertionError(
            f"{path}:{line_number} must contain '=' for env key-value structure."
        )

    key, _ = line.split("=", 1)
    key = key.strip()
    if not key:
        raise AssertionError(f"{path}:{line_number} has an empty key before '='.")

    return key


def test_tracked_env_files_have_aligned_line_structure_and_keys(
    repo_root: Path,
) -> None:
    env_dir = repo_root / "infra" / "env"
    env_files = [env_dir / name for name in ENV_FILENAMES]

    baseline_file = env_files[0]
    baseline_lines = baseline_file.read_text(encoding="utf-8").splitlines()
    assert baseline_lines, f"{baseline_file} must not be empty."

    for file_path in env_files[1:]:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == len(baseline_lines), (
            f"{file_path} line count must match {baseline_file}: "
            f"{len(lines)} != {len(baseline_lines)}"
        )

        for line_number, (baseline_line, line) in enumerate(
            zip(baseline_lines, lines, strict=True),
            start=1,
        ):
            baseline_kind = _line_kind(baseline_line)
            kind = _line_kind(line)
            assert kind == baseline_kind, (
                f"{file_path}:{line_number} structure mismatch with "
                f"{baseline_file}:{line_number} ({kind} != {baseline_kind})"
            )

            if baseline_kind == "key_value":
                baseline_key = _parse_env_key(
                    path=baseline_file,
                    line_number=line_number,
                    line=baseline_line,
                )
                key = _parse_env_key(path=file_path, line_number=line_number, line=line)
                assert key == baseline_key, (
                    f"{file_path}:{line_number} key '{key}' must align with "
                    f"{baseline_file}:{line_number} key '{baseline_key}'."
                )
