"""
Abstract: Unit tests for MCP PAT fingerprinting.
Out of scope: Bearer parsing and token-exchange cache storage.
"""

from __future__ import annotations

from knowledge_mcp.auth.fingerprint import fingerprint_pat


def test_fingerprint_is_deterministic_for_same_secret_and_pat() -> None:
    first = fingerprint_pat("pat_secret_value", secret="x" * 32)
    second = fingerprint_pat("pat_secret_value", secret="x" * 32)

    assert first == second


def test_fingerprint_changes_when_secret_changes() -> None:
    first = fingerprint_pat("pat_secret_value", secret="x" * 32)
    second = fingerprint_pat("pat_secret_value", secret="y" * 32)

    assert first != second


def test_fingerprint_does_not_contain_raw_pat() -> None:
    fingerprint = fingerprint_pat("pat_secret_value", secret="x" * 32)

    assert "pat_secret_value" not in fingerprint
    assert fingerprint.startswith("pat_")
