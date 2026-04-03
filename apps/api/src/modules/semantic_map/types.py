"""
Abstract: Shared semantic-map type aliases for snapshot payload and coordinate records.
Out of scope: SQLAlchemy model declarations and repository query execution.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

type Bounds4 = tuple[float, float, float, float]
type Point2 = tuple[float, float]


class SemanticMapPayloadModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)


class StoredDefaultViewPayload(SemanticMapPayloadModel):
    target: list[float]
    zoom: float


class PolygonGeometryPayload(SemanticMapPayloadModel):
    type: Literal["polygon"]
    coordinates: list[list[float]]


class MultiPolygonGeometryPayload(SemanticMapPayloadModel):
    type: Literal["multi_polygon"]
    coordinates: list[list[list[float]]]


type RegionGeometryPayload = Annotated[
    PolygonGeometryPayload | MultiPolygonGeometryPayload,
    Field(discriminator="type"),
]


class RegionPayload(SemanticMapPayloadModel):
    id: str
    parent_id: str | None
    region_name: str
    centroid: list[float]
    bbox: list[float]
    geometry: RegionGeometryPayload
    display_rank: int
    children_available: bool


class LabelPayload(SemanticMapPayloadModel):
    id: str
    region_id: str
    text: str
    position: list[float]
    label_rank: int
    font_size: int
