"""
Abstract: Search orchestration service for query embedding and knowledge lookups.
Out of scope: FastAPI transport wiring and direct database access.
"""

from __future__ import annotations

from core.errors import ErrorCode, InfrastructureError
from modules.knowledge_graph.ports import KnowledgeGraphReadPort
from modules.search.schema import MatchedCardResponse, SearchResponse
from shared.integrations import EmbeddingClientPort, EmbeddingServiceUnavailableError


class SearchService:
    def __init__(
        self,
        *,
        knowledge_graph_read_port: KnowledgeGraphReadPort,
        embedding_client: EmbeddingClientPort,
        max_matched: int,
        max_connected: int,
    ) -> None:
        self._knowledge_graph_read_port = knowledge_graph_read_port
        self._embedding_client = embedding_client
        self._max_matched = max_matched
        self._max_connected = max_connected

    async def search(self, query: str) -> SearchResponse:
        try:
            query_embedding = await self._embedding_client.embed_text(query)
        except EmbeddingServiceUnavailableError as exc:
            raise InfrastructureError(
                code=ErrorCode.INFRA_EMBEDDING_SERVICE_UNAVAILABLE,
                message="Search dependency unavailable.",
                hint="Retry the search later.",
                safe_details={"dependency": "embedding_service"},
                log_details={"reason": str(exc)},
            ) from exc

        matched_records = await self._knowledge_graph_read_port.search_searchable_cards(
            query_embedding=query_embedding,
            limit=self._max_matched,
        )

        matched_cards = [
            MatchedCardResponse(
                node_id=item.node_id,
                current_version=item.current_version,
                title=item.title,
                content=item.content,
            )
            for item in matched_records
        ]
        connected_titles = await self._knowledge_graph_read_port.get_connected_titles(
            matched_node_ids=[item.node_id for item in matched_records],
            excluded_titles={item.title for item in matched_records},
            limit=self._max_connected,
        )

        return SearchResponse(
            matched_cards=matched_cards,
            connected_titles=connected_titles,
        )
