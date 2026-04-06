"""
Abstract: Integration-style build test across knowledge materialization and
semantic-map snapshot generation.
Out of scope: Real PostgreSQL networking and FastAPI route transport assertions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from modules.knowledge_graph.dto import (
    ConnectedTitleCandidate,
    KnowledgeCardMatch,
    SemanticMapProjectionEdge,
    SemanticMapProjectionNode,
    SimilarNodeCandidate,
)
from modules.knowledge_graph.service import KnowledgeGraphService
from modules.semantic_map.core.dto import SemanticMapManifest, SemanticMapRegionTile
from modules.semantic_map.snapshot_build.service import SemanticMapBuildService
from modules.taxonomy.dto import TaxonomyNodeRecord, TaxonomySemanticMapAssignment


@dataclass(slots=True)
class _StoredNode:
    node_id: int
    title: str
    content: str
    embedding: list[float]


@dataclass(slots=True)
class _InMemoryKnowledgeRepo:
    nodes: list[_StoredNode] = field(default_factory=list)

    async def search_top_cards_by_cosine(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeCardMatch]:
        raise AssertionError("search_top_cards_by_cosine is not used in this flow")

    async def fetch_connected_title_candidates(
        self,
        *,
        matched_node_ids: Sequence[int],
    ) -> list[ConnectedTitleCandidate]:
        return []

    async def create_node(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        node_id = len(self.nodes) + 1
        self.nodes.append(
            _StoredNode(
                node_id=node_id,
                title=title,
                content=content,
                embedding=embedding,
            )
        )
        return node_id

    async def search_similarity_candidates(
        self,
        *,
        query_embedding: list[float],
        excluded_node_ids: Sequence[int],
    ) -> list[SimilarNodeCandidate]:
        return []

    async def create_edge_with_adjacency(
        self,
        *,
        source_node_id: int,
        related_node_id: int,
        strength: float,
    ) -> None:
        raise AssertionError("create_edge_with_adjacency is not used in this flow")

    async def fetch_projection_nodes(self) -> list[SemanticMapProjectionNode]:
        return [
            SemanticMapProjectionNode(
                node_id=node.node_id,
                title=node.title,
                embedding=node.embedding,
            )
            for node in self.nodes
        ]

    async def fetch_projection_nodes_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[SemanticMapProjectionNode]:
        return [
            SemanticMapProjectionNode(
                node_id=node.node_id,
                title=node.title,
                embedding=node.embedding,
            )
            for node in self.nodes
            if node.node_id in node_ids
        ]

    async def fetch_projection_edges_for_node_ids(
        self,
        *,
        node_ids: Sequence[int],
    ) -> list[SemanticMapProjectionEdge]:
        return []

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@dataclass(slots=True)
class _RecordingSnapshotRepo:
    published_manifest: SemanticMapManifest | None = None
    published_tiles: list[SemanticMapRegionTile] | None = None

    async def publish_snapshot(
        self,
        *,
        manifest: SemanticMapManifest,
        tiles: Sequence[SemanticMapRegionTile],
    ) -> None:
        self.published_manifest = manifest
        self.published_tiles = list(tiles)


@dataclass(slots=True)
class _StubTaxonomyPort:
    assigned_leaf_depths: list[int]
    tree_nodes: list[TaxonomyNodeRecord]
    assignments: list[TaxonomySemanticMapAssignment]

    async def list_assigned_leaf_depths_for_semantic_map(self) -> list[int]:
        return list(self.assigned_leaf_depths)

    async def list_tree_nodes_for_semantic_map(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def list_semantic_map_assignments(self) -> list[TaxonomySemanticMapAssignment]:
        return list(self.assignments)


@pytest.mark.integration
@pytest.mark.anyio
async def test_build_consumes_knowledge_projection_nodes_and_publishes_snapshot() -> None:
    knowledge_service = KnowledgeGraphService(
        repo=_InMemoryKnowledgeRepo(),
        edge_similarity_top_k=2,
        edge_similarity_min_strength=0.0,
    )
    snapshot_repo = _RecordingSnapshotRepo()
    taxonomy_port = _StubTaxonomyPort(
        assigned_leaf_depths=[2],
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Science", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Math", depth=1, is_leaf=False),
            TaxonomyNodeRecord(id=3, parent_id=2, name="Algebra", depth=2, is_leaf=True),
        ],
        assignments=[
            TaxonomySemanticMapAssignment(node_id=1, taxonomy_leaf_id=3),
            TaxonomySemanticMapAssignment(node_id=2, taxonomy_leaf_id=3),
            TaxonomySemanticMapAssignment(node_id=3, taxonomy_leaf_id=3),
        ],
    )
    build_service = SemanticMapBuildService(
        projection_port=knowledge_service,
        taxonomy_port=taxonomy_port,
        snapshot_repo=snapshot_repo,
        now=lambda: datetime(2026, 4, 3, 15, 30, tzinfo=UTC),
    )

    await knowledge_service.materialize_card_from_ingestion(
        title="Alpha",
        content="Alpha content",
        embedding=[1.0, 0.0, 0.0],
    )
    await knowledge_service.materialize_card_from_ingestion(
        title="Beta",
        content="Beta content",
        embedding=[0.9, 0.1, 0.0],
    )
    await knowledge_service.materialize_card_from_ingestion(
        title="Gamma",
        content="Gamma content",
        embedding=[0.0, 1.0, 0.0],
    )

    version = await build_service.build_current_snapshot()

    assert version == "20260403_153000_000000"
    assert snapshot_repo.published_manifest is not None
    assert snapshot_repo.published_manifest.schema_version == "20260403_153000_000000"
    assert snapshot_repo.published_tiles is not None
    assert any(tile.region_count > 0 for tile in snapshot_repo.published_tiles)
    assert any(tile.points for tile in snapshot_repo.published_tiles)
