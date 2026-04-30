"""
Abstract: Worker instruction builder for taxonomy-classification queue jobs.
Out of scope: Queue transport and local result persistence.
"""

from __future__ import annotations


def build_taxonomy_classification_instruction() -> str:
    return (
        "Classify the supplied card within the supplied taxonomy scope path into exactly "
        "one supplied direct child taxonomy category, or keep it in Unclassified when none "
        "of the children fit."
    )


__all__ = ["build_taxonomy_classification_instruction"]
