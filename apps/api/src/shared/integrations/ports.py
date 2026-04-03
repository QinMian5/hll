"""
Abstract: Shared protocol contracts for integration clients consumed by modules.
Out of scope: HTTP client implementation and runtime dependency composition.
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingClientPort(Protocol):
    async def embed_text(self, text: str) -> list[float]: ...


__all__ = ["EmbeddingClientPort"]
