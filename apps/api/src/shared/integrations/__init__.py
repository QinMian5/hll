"""
Abstract: Public exports for shared runtime integration clients used across backend
modules.
Out of scope: Queue broker setup and module-specific orchestration logic.
"""

from shared.integrations.embedding_client import EmbeddingClient, build_embedding_client
from shared.integrations.ports import EmbeddingClientPort

__all__ = ["EmbeddingClient", "EmbeddingClientPort", "build_embedding_client"]
