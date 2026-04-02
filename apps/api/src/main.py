"""
Abstract: Compatibility module exporting the API app entrypoint object.
Out of scope: Runtime dependency wiring and route registration details.
"""

from __future__ import annotations

from entrypoints.api.app import app as _app

app = _app

__all__ = ["app"]
