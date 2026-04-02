"""
Abstract: Service-port protocols exposed by the knowledge-graph domain core.
Out of scope: HTTP transport contracts and infrastructure client configuration.
"""

from __future__ import annotations

from typing import Protocol

from modules.knowledge_graph.dto import KnowledgeCardMatch


class KnowledgeGraphReadPort(Protocol):
    async def search_searchable_cards(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]: ...

    async def get_connected_titles(
        self,
        *,
        matched_node_ids: list[int],
        excluded_titles: set[str],
        limit: int,
    ) -> list[str]: ...


class KnowledgeGraphWritePort(Protocol):
    async def materialize_card_from_ingestion(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int: ...
