"""
Abstract: Unit tests for taxonomy-classification job payload and result contracts.
Out of scope: Queue transport behavior and taxonomy assignment mutation.
"""

from __future__ import annotations

import pytest

from modules.taxonomy_classification.contracts import (
    TaxonomyClassificationAcceptedResult,
    TaxonomyClassificationJobPayload,
    export_taxonomy_classification_output_schema,
)


def test_job_payload_carries_scope_card_children_and_unclassified_option() -> None:
    payload = TaxonomyClassificationJobPayload.model_validate(
        {
            "scope_node": {"id": 10, "name": "Science"},
            "source_unclassified_node": {"id": 11, "name": "Unclassified"},
            "card": {"id": 41, "title": "Linear Algebra", "content": "Vector spaces"},
            "children": [
                {"id": 20, "name": "Mathematics"},
                {"id": 30, "name": "Physics"},
            ],
            "allow_unclassified": True,
        }
    )

    assert payload.scope_node.id == 10
    assert payload.source_unclassified_node.name == "Unclassified"
    assert [child.name for child in payload.children] == ["Mathematics", "Physics"]
    assert payload.allow_unclassified is True


def test_accepted_result_allows_child_target() -> None:
    result = TaxonomyClassificationAcceptedResult.model_validate(
        {
            "target": {
                "kind": "child",
                "child_id": 20,
                "reason": "The card discusses mathematics.",
            }
        }
    )

    assert result.target.kind == "child"
    assert result.target.child_id == 20


def test_accepted_result_requires_child_id_for_child_target() -> None:
    with pytest.raises(ValueError, match="child_id"):
        TaxonomyClassificationAcceptedResult.model_validate(
            {"target": {"kind": "child", "reason": "Missing child id."}}
        )


def test_accepted_result_keeps_unclassified_without_child_id() -> None:
    result = TaxonomyClassificationAcceptedResult.model_validate(
        {"target": {"kind": "unclassified", "reason": "No direct child fits."}}
    )

    assert result.target.kind == "unclassified"
    assert result.target.child_id is None


def test_output_schema_exports_target_shape_for_job_queue() -> None:
    schema = export_taxonomy_classification_output_schema()

    assert schema["type"] == "object"
    assert "target" in schema["properties"]
