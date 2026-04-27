"""
Abstract: Unit tests for embedding-client external dependency error handling.
Out of scope: Real embedding provider connectivity and response ranking behavior.
"""

from __future__ import annotations

from types import TracebackType

import httpx
import pytest

from shared.integrations.embedding_client import EmbeddingClient, EmbeddingServiceUnavailableError


class _ConnectFailingAsyncClient:
    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> _ConnectFailingAsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        json: dict[str, str],
        headers: dict[str, str],
    ) -> httpx.Response:
        assert url == "https://api.openai.com/v1/embeddings"
        assert json == {"model": "text-embedding-3-small", "input": "search query"}
        assert headers == {"Authorization": "Bearer secret"}
        raise httpx.ConnectError("dns unavailable")


@pytest.mark.anyio
async def test_embedding_client_wraps_connect_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", _ConnectFailingAsyncClient)
    client = EmbeddingClient(
        api_url="https://api.openai.com/v1/embeddings",
        model="text-embedding-3-small",
        timeout_seconds=1.0,
        api_key="secret",
    )

    with pytest.raises(EmbeddingServiceUnavailableError) as exc_info:
        await client.embed_text("search query")

    assert "request failed" in str(exc_info.value)
