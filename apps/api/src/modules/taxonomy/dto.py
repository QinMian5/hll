"""
Abstract: Pydantic DTOs used by the taxonomy bootstrap importer.
Out of scope: SQLAlchemy persistence mapping and HTTP transport contracts.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TaxonomyPath = tuple[NonEmptyString, ...]


class TaxonomyImportNode(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    path: TaxonomyPath = Field(min_length=1)
    parent_path: TaxonomyPath | None = None
    name: NonEmptyString
    depth: int = Field(ge=0)
    is_leaf: bool
