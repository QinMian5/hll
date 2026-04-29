"""
Abstract: Worker instruction builder for taxonomy-classification queue jobs.
Out of scope: Queue transport and local result persistence.
"""

from __future__ import annotations


def build_taxonomy_classification_instruction() -> str:
    return (
        "Classify the supplied card into exactly one of the supplied direct child "
        "taxonomy categories, or keep it in the source Unclassified bucket when none "
        "of the children fit. Return only JSON matching the supplied output schema. "
        "When selecting a child, use target.kind='child' and the exact child_id from "
        "the payload. Do not choose a parent, ancestor, sibling, new category, or "
        "any child not listed in the payload. When no child fits, use "
        "target.kind='unclassified'."
    )


__all__ = ["build_taxonomy_classification_instruction"]
