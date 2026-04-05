"""
Abstract: Module-local exception types for taxonomy bootstrap and assignment workflows.
Out of scope: API error-envelope contracts and HTTP status mapping.
"""

from __future__ import annotations


class TaxonomyImportError(RuntimeError):
    pass
