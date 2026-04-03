"""
Abstract: Pure 2D geometry helpers used by semantic-map snapshot materialization.
Out of scope: Projection/clustering orchestration and SQLAlchemy persistence behavior.
"""

from __future__ import annotations

from collections.abc import Sequence

from modules.semantic_map.types import Bounds4, Point2, PolygonGeometryPayload


def _cross(origin: Point2, point_a: Point2, point_b: Point2) -> float:
    return (point_a[0] - origin[0]) * (point_b[1] - origin[1]) - (point_a[1] - origin[1]) * (
        point_b[0] - origin[0]
    )


def compute_bbox(points: Sequence[Point2]) -> Bounds4:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def compute_centroid(points: Sequence[Point2]) -> Point2:
    count = float(len(points))
    return (
        sum(point[0] for point in points) / count,
        sum(point[1] for point in points) / count,
    )


def bounds_intersect(bounds_a: Bounds4, bounds_b: Bounds4) -> bool:
    return not (
        bounds_a[2] < bounds_b[0]
        or bounds_b[2] < bounds_a[0]
        or bounds_a[3] < bounds_b[1]
        or bounds_b[3] < bounds_a[1]
    )


def point_in_bounds(point: Point2, bounds: Bounds4) -> bool:
    return bounds[0] <= point[0] <= bounds[2] and bounds[1] <= point[1] <= bounds[3]


def _build_rectangle(points: Sequence[Point2]) -> list[Point2]:
    min_x, min_y, max_x, max_y = compute_bbox(points)
    padding = max(max_x - min_x, max_y - min_y, 1.0) * 0.1
    return [
        (min_x - padding, min_y - padding),
        (max_x + padding, min_y - padding),
        (max_x + padding, max_y + padding),
        (min_x - padding, max_y + padding),
    ]


def _convex_hull(points: Sequence[Point2]) -> list[Point2]:
    unique_points = sorted(set(points))
    if len(unique_points) <= 2:
        return _build_rectangle(unique_points)

    lower: list[Point2] = []
    for point in unique_points:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper: list[Point2] = []
    for point in reversed(unique_points):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return _build_rectangle(unique_points)
    return hull


def build_cluster_hull(points: Sequence[Point2]) -> PolygonGeometryPayload:
    polygon = _convex_hull(points)
    closed_polygon = [*polygon, polygon[0]]
    return PolygonGeometryPayload(
        type="polygon",
        coordinates=[[point[0], point[1]] for point in closed_polygon],
    )
