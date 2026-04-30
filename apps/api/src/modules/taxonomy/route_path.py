"""
Abstract: Canonical taxonomy route-slug and route-path helpers.
Out of scope: Taxonomy persistence queries and HTTP transport behavior.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_ROUTE_SLUG_SEPARATOR_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify_taxonomy_route_segment(name: str) -> str:
    slug = _ROUTE_SLUG_SEPARATOR_PATTERN.sub("-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Taxonomy route slug must contain at least one ASCII letter or digit.")
    return slug


def join_taxonomy_route_path(route_slugs: Iterable[str]) -> str:
    return "/".join(slug for slug in route_slugs if slug)
