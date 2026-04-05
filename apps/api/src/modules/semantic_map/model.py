"""
Abstract: SQLAlchemy persistence projection for semantic-map snapshots and region tiles.
Out of scope: Rebuild orchestration and HTTP transport contracts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from modules.semantic_map.types import (
    JsonObject,
)
from shared.db.base import Base


class SemanticMapSnapshot(Base):
    __tablename__ = "semantic_map_snapshots"
    __table_args__ = (
        UniqueConstraint("version", name="uq_semantic_map_snapshots_version"),
        Index(
            "uq_semantic_map_snapshots_current_true",
            "current",
            unique=True,
            postgresql_where=text("current"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    built_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    world_bounds: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    tile_size: Mapped[int] = mapped_column(Integer, nullable=False)
    max_zoom: Mapped[int] = mapped_column(Integer, nullable=False)
    default_view: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    default_semantic_level: Mapped[int] = mapped_column(Integer, nullable=False)
    semantic_levels: Mapped[list[JsonObject]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'[]'::json"),
    )


class SemanticMapRegionTile(Base):
    __tablename__ = "semantic_map_region_tiles"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "semantic_level",
            "tile_z",
            "tile_x",
            "tile_y",
            name="uq_semantic_map_region_tiles_snapshot_level_tile",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("semantic_map_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    semantic_level: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_z: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_x: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_y: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_bounds: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    region_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    regions: Mapped[list[JsonObject]] = mapped_column(JSON, nullable=False)
    labels: Mapped[list[JsonObject]] = mapped_column(JSON, nullable=False)
    points: Mapped[list[JsonObject]] = mapped_column(
        JSON,
        nullable=False,
        server_default=text("'[]'::json"),
    )
