"""
Abstract: Async SQLAlchemy repository primitives for semantic-map snapshot reads and publication.
Out of scope: Projection/clustering computation and HTTP endpoint behavior.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import TypeAdapter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from modules.semantic_map.dto import (
    DefaultView,
    SemanticMapManifest,
)
from modules.semantic_map.dto import (
    SemanticMapRegionTile as SemanticMapRegionTileValue,
)
from modules.semantic_map.model import (
    SemanticMapRegionTile as SemanticMapRegionTileModel,
)
from modules.semantic_map.model import (
    SemanticMapSnapshot,
)
from modules.semantic_map.types import (
    Bounds4,
    JsonObject,
    LabelPayload,
    Point2,
    RegionPayload,
    StoredDefaultViewPayload,
)

_DEFAULT_VIEW_PAYLOAD_ADAPTER = TypeAdapter(StoredDefaultViewPayload)
_REGION_PAYLOADS_ADAPTER = TypeAdapter(list[RegionPayload])
_LABEL_PAYLOADS_ADAPTER = TypeAdapter(list[LabelPayload])


def _bounds4_from_stored(values: Sequence[float]) -> Bounds4:
    return (values[0], values[1], values[2], values[3])


def _point2_from_stored(values: Sequence[float]) -> Point2:
    return (values[0], values[1])


def _default_view_from_stored(payload: JsonObject) -> DefaultView:
    stored_payload = _DEFAULT_VIEW_PAYLOAD_ADAPTER.validate_python(payload)
    return DefaultView(
        target=_point2_from_stored(stored_payload.target),
        zoom=stored_payload.zoom,
    )


class SemanticMapRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def get_current_manifest(self) -> SemanticMapManifest | None:
        snapshot = await self._session.scalar(
            select(SemanticMapSnapshot)
            .where(SemanticMapSnapshot.current.is_(True))
            .order_by(SemanticMapSnapshot.built_at.desc())
            .limit(1)
        )
        return None if snapshot is None else _manifest_from_snapshot(snapshot)

    async def get_manifest_by_version(self, *, version: str) -> SemanticMapManifest | None:
        snapshot = await self._session.scalar(
            select(SemanticMapSnapshot).where(SemanticMapSnapshot.version == version).limit(1)
        )
        return None if snapshot is None else _manifest_from_snapshot(snapshot)

    async def get_region_tile(
        self,
        *,
        version: str,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
    ) -> SemanticMapRegionTileValue | None:
        tile = await self._session.scalar(
            select(SemanticMapRegionTileModel)
            .join(
                SemanticMapSnapshot,
                SemanticMapSnapshot.id == SemanticMapRegionTileModel.snapshot_id,
            )
            .where(
                SemanticMapSnapshot.version == version,
                SemanticMapRegionTileModel.semantic_level == semantic_level,
                SemanticMapRegionTileModel.tile_z == tile_z,
                SemanticMapRegionTileModel.tile_x == tile_x,
                SemanticMapRegionTileModel.tile_y == tile_y,
            )
            .limit(1)
        )
        if tile is None:
            return None

        return SemanticMapRegionTileValue(
            semantic_level=tile.semantic_level,
            tile_z=tile.tile_z,
            tile_x=tile.tile_x,
            tile_y=tile.tile_y,
            tile_bounds=_bounds4_from_stored(tile.tile_bounds),
            region_count=tile.region_count,
            label_count=tile.label_count,
            regions=_REGION_PAYLOADS_ADAPTER.validate_python(tile.regions),
            labels=_LABEL_PAYLOADS_ADAPTER.validate_python(tile.labels),
        )

    async def publish_snapshot(
        self,
        *,
        manifest: SemanticMapManifest,
        tiles: Sequence[SemanticMapRegionTileValue],
    ) -> None:
        await self._session.execute(
            update(SemanticMapSnapshot)
            .where(SemanticMapSnapshot.current.is_(True))
            .values(current=False)
        )

        snapshot = SemanticMapSnapshot(
            version=manifest.version,
            schema_version=manifest.schema_version,
            built_at=manifest.built_at,
            current=True,
            world_bounds=list(manifest.world_bounds),
            tile_size=manifest.tile_size,
            max_zoom=manifest.max_zoom,
            default_view=StoredDefaultViewPayload(
                target=list(manifest.default_view.target),
                zoom=manifest.default_view.zoom,
            ).model_dump(mode="json"),
            default_semantic_level=manifest.default_semantic_level,
        )
        self._session.add(snapshot)
        await self._session.flush()

        self._session.add_all(
            SemanticMapRegionTileModel(
                snapshot_id=snapshot.id,
                semantic_level=tile.semantic_level,
                tile_z=tile.tile_z,
                tile_x=tile.tile_x,
                tile_y=tile.tile_y,
                tile_bounds=list(tile.tile_bounds),
                region_count=tile.region_count,
                label_count=tile.label_count,
                regions=[region.model_dump(mode="json") for region in tile.regions],
                labels=[label.model_dump(mode="json") for label in tile.labels],
            )
            for tile in tiles
        )

        await self._session.commit()


def _manifest_from_snapshot(snapshot: SemanticMapSnapshot) -> SemanticMapManifest:
    return SemanticMapManifest(
        version=snapshot.version,
        schema_version=snapshot.schema_version,
        built_at=snapshot.built_at,
        world_bounds=_bounds4_from_stored(snapshot.world_bounds),
        tile_size=snapshot.tile_size,
        max_zoom=snapshot.max_zoom,
        default_view=_default_view_from_stored(snapshot.default_view),
        default_semantic_level=snapshot.default_semantic_level,
    )
