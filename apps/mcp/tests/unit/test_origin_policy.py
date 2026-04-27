"""
Abstract: Unit tests for MCP browser Origin policy.
Out of scope: Bearer-token authentication and MCP protocol handling.
"""

from __future__ import annotations

from knowledge_mcp.http_app import is_origin_allowed


def test_request_without_origin_is_allowed_for_non_browser_clients() -> None:
    assert is_origin_allowed(None, allowed_origins=("https://knowledge.example.com",))


def test_configured_origin_is_allowed() -> None:
    assert is_origin_allowed(
        "https://knowledge.example.com",
        allowed_origins=("https://knowledge.example.com",),
    )


def test_unconfigured_origin_is_rejected() -> None:
    assert not is_origin_allowed(
        "https://evil.example.com",
        allowed_origins=("https://knowledge.example.com",),
    )
