"""
Abstract: Search orchestration service for query embedding and knowledge lookups.
Out of scope: FastAPI transport wiring and direct database access.
"""

from __future__ import annotations

from typing import Protocol

from modules.knowledge_graph.ports import KnowledgeGraphReadPort
from modules.search.schema import MatchedCardResponse, SearchResponse


class EmbeddingClientProtocol(Protocol):
    async def embed_text(self, text: str) -> list[float]: ...


class SearchService:
    def __init__(
        self,
        *,
        knowledge_graph_read_port: KnowledgeGraphReadPort,
        embedding_client: EmbeddingClientProtocol,
        max_matched: int,
        max_connected: int,
    ) -> None:
        self._knowledge_graph_read_port = knowledge_graph_read_port
        self._embedding_client = embedding_client
        self._max_matched = max_matched
        self._max_connected = max_connected

    async def search(self, query: str) -> SearchResponse:
        query_embedding = await self._embedding_client.embed_text(query)
        matched_records = await self._knowledge_graph_read_port.search_searchable_cards(
            query_embedding=query_embedding,
            limit=self._max_matched,
        )

        matched_cards = [
            MatchedCardResponse(title=item.title, content=item.content)
            for item in matched_records
        ]
        connected_titles = await self._knowledge_graph_read_port.get_connected_titles(
            matched_node_ids=[
                item.node_id for item in matched_records if item.node_id is not None
            ],
            excluded_titles={item.title for item in matched_records},
            limit=self._max_connected,
        )

        return SearchResponse(
            matched_cards=matched_cards,
            connected_titles=connected_titles,
        )
