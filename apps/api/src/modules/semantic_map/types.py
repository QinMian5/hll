"""
Abstract: Shared semantic-map type aliases for snapshot payload and coordinate records.
Out of scope: SQLAlchemy model declarations and repository query execution.
"""

from __future__ import annotations

from typing import TypedDict

type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

type Bounds4 = tuple[float, float, float, float]
type Point2 = tuple[float, float]


class StoredDefaultViewPayload(TypedDict):
    target: list[float]
    zoom: float
