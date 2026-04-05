"""
Abstract: Dependency contracts for semantic-map read and rebuild services.
Out of scope: SQLAlchemy repository implementation and FastAPI wiring.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from modules.semantic_map.dto import SemanticMapManifest, SemanticMapRegionTile


class SemanticMapSnapshotReadPort(Protocol):
    async def get_current_manifest(self) -> SemanticMapManifest | None: ...

    async def get_manifest_by_version(self, *, version: str) -> SemanticMapManifest | None: ...

    async def get_region_tile(
        self,
        *,
        version: str,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
    ) -> SemanticMapRegionTile | None: ...


class SemanticMapSnapshotWritePort(Protocol):
    async def publish_snapshot(
        self,
        *,
        manifest: SemanticMapManifest,
        tiles: Sequence[SemanticMapRegionTile],
    ) -> None: ...


class TaxonomyAssignedNodesPort(Protocol):
    async def list_assigned_node_ids_for_semantic_map(self) -> list[int]: ...
