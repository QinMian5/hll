"""
Abstract: Service-port protocols exposed by the knowledge-graph domain core.
Out of scope: HTTP transport contracts and infrastructure client configuration.
"""

from __future__ import annotations

from typing import Protocol

from modules.knowledge_graph.dto import (
    KnowledgeCardMatch,
    SemanticMapProjectionEdge,
    SemanticMapProjectionNode,
    TaxonomyClassificationNodeInput,
)


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


class KnowledgeGraphProjectionPort(Protocol):
    async def list_projection_nodes_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[SemanticMapProjectionNode]: ...

    async def list_projection_nodes_for_semantic_map(self) -> list[SemanticMapProjectionNode]: ...

    async def list_projection_edges_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[SemanticMapProjectionEdge]: ...

    async def list_unassigned_nodes_for_taxonomy_classification(
        self,
        *,
        limit: int | None,
    ) -> list[TaxonomyClassificationNodeInput]: ...


class KnowledgeGraphWritePort(Protocol):
    async def materialize_card_from_ingestion(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int: ...
