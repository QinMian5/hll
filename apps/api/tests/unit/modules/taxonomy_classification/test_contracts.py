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


def test_job_payload_carries_scope_path_card_and_child_names_without_ids() -> None:
    payload = TaxonomyClassificationJobPayload.model_validate(
        {
            "scope_path": "Root / Science",
            "card": {"title": "Linear Algebra", "content": "Vector spaces"},
            "children": [
                {"name": "Mathematics"},
                {"name": "Physics"},
            ],
        }
    )

    assert payload.scope_path == "Root / Science"
    assert payload.card.title == "Linear Algebra"
    assert [child.name for child in payload.children] == ["Mathematics", "Physics"]


def test_job_payload_rejects_internal_ids_and_source_leaf_context() -> None:
    with pytest.raises(ValueError, match=r"extra_forbidden"):
        TaxonomyClassificationJobPayload.model_validate(
            {
                "scope_node": {"id": 10, "name": "Science"},
                "source_unclassified_node": {"id": 11, "name": "Unclassified"},
                "card": {"id": 41, "title": "Linear Algebra", "content": "Vector spaces"},
                "children": [{"id": 20, "name": "Mathematics"}],
                "allow_unclassified": True,
            }
        )


def test_accepted_result_allows_child_name_target() -> None:
    result = TaxonomyClassificationAcceptedResult.model_validate({"target_name": "Mathematics"})

    assert result.target_name == "Mathematics"


def test_accepted_result_allows_unclassified_target_by_name() -> None:
    result = TaxonomyClassificationAcceptedResult.model_validate({"target_name": "unclassified"})

    assert result.target_name == "unclassified"


def test_accepted_result_rejects_legacy_kind_reason_and_id_shape() -> None:
    with pytest.raises(ValueError, match=r"extra_forbidden"):
        TaxonomyClassificationAcceptedResult.model_validate(
            {
                "target": {
                    "kind": "child",
                    "child_id": 20,
                    "reason": "The card discusses mathematics.",
                }
            }
        )


def test_output_schema_exports_target_shape_for_job_queue() -> None:
    schema = export_taxonomy_classification_output_schema()

    assert schema["type"] == "object"
    assert "target_name" in schema["properties"]
    assert "target" not in schema["properties"]
