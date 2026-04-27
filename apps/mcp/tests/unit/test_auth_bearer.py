"""
Abstract: Unit tests for MCP bearer-token extraction.
Out of scope: Logto token exchange and JWT claim validation.
"""

from __future__ import annotations

import pytest

from knowledge_mcp.auth.bearer import AuthenticationError, extract_bearer_token


@pytest.mark.parametrize("authorization", [None, "", "Basic abc", "Bearer", "Bearer   "])
def test_missing_or_non_bearer_authorization_is_rejected(authorization: str | None) -> None:
    with pytest.raises(AuthenticationError):
        extract_bearer_token(authorization)


def test_valid_bearer_authorization_returns_token() -> None:
    token = extract_bearer_token("Bearer pat_test_token")

    assert token == "pat_test_token"


def test_bearer_scheme_is_case_insensitive() -> None:
    token = extract_bearer_token("bearer pat_test_token")

    assert token == "pat_test_token"
