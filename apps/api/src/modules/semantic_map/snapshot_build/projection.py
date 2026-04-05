"""
Abstract: Project semantic-map embedding vectors into normalized 2D coordinates.
Out of scope: Taxonomy aggregation, tile emission, and snapshot persistence.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.decomposition import PCA

from modules.knowledge_graph.dto import SemanticMapProjectionNode
from modules.semantic_map.core.types import Point2


def _normalize_projected_points(points: Sequence[Point2]) -> list[Point2]:
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)

    def _scale(value: float, *, lower: float, upper: float) -> float:
        if upper == lower:
            return 500.0
        return 100.0 + ((value - lower) / (upper - lower)) * 800.0

    return [
        (
            _scale(point[0], lower=min_x, upper=max_x),
            _scale(point[1], lower=min_y, upper=max_y),
        )
        for point in points
    ]


def project_points(nodes: Sequence[SemanticMapProjectionNode]) -> list[Point2]:
    if len(nodes) == 1:
        return [(500.0, 500.0)]

    matrix = np.asarray([node.embedding for node in nodes], dtype=float)
    projected = PCA(n_components=2).fit_transform(matrix)
    return _normalize_projected_points([(float(row[0]), float(row[1])) for row in projected])
