"""
Abstract: Unit tests for global app-error payload contract and error-code enum
governance.
Out of scope: FastAPI exception handlers, HTTP status mapping, and OpenAPI
schema wiring.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

import pytest
from pydantic import ValidationError

from core.errors import (
    AppError,
    ApplicationError,
    DomainError,
    ErrorCode,
    ErrorPayload,
    InfrastructureError,
    InternalError,
)

ERROR_CODE_VALUE_PATTERN = re.compile(r"^[A-Z0-9]+(?:_[A-Z0-9]+){2,}$")


def test_error_code_is_str_enum() -> None:
    assert issubclass(ErrorCode, StrEnum)
    assert isinstance(ErrorCode.APPLICATION_API_INPUT_INVALID, str)


def test_error_code_values_follow_domain_category_detail_format() -> None:
    for code in ErrorCode:
        assert ERROR_CODE_VALUE_PATTERN.match(code.value)


def test_error_code_values_are_unique() -> None:
    values = [code.value for code in ErrorCode]
    assert len(values) == len(set(values))


def test_error_code_enum_uses_only_allowed_domain_segments() -> None:
    allowed_domains = {"APPLICATION", "DOMAIN", "INFRA", "INTERNAL"}
    for code in ErrorCode:
        domain, _, _ = code.value.split("_", 2)
        assert domain in allowed_domains


def test_app_error_payload_contains_unified_contract_fields() -> None:
    error = AppError(
        code=ErrorCode.DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND,
        message="Node not found.",
        hint="Verify the node id and retry.",
        safe_details={"node_id": 42},
    )

    payload = error.to_response_payload(request_id="req_12345678")

    assert isinstance(payload, ErrorPayload)
    assert payload.model_dump() == {
        "code": ErrorCode.DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND.value,
        "message": "Node not found.",
        "details": {"node_id": 42},
        "hint": "Verify the node id and retry.",
        "request_id": "req_12345678",
    }


def test_app_error_defaults_details_to_empty_object() -> None:
    error = AppError(
        code=ErrorCode.APPLICATION_API_INPUT_INVALID,
        message="Invalid input.",
        hint="Adjust request parameters and retry.",
    )

    payload = error.to_response_payload(request_id="req_12345678")
    assert payload.details == {}


def test_app_error_rejects_empty_hint() -> None:
    with pytest.raises(ValidationError):
        AppError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION,
            message="Rule violated.",
            hint="   ",
        ).to_response_payload(request_id="req_12345678")


def test_app_error_rejects_non_dict_safe_details() -> None:
    invalid_payload: dict[str, Any] = {
        "code": ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION,
        "message": "Rule violated.",
        "hint": "Fix input and retry.",
        "safe_details": ["not", "a", "dict"],
    }
    with pytest.raises(ValidationError):
        AppError(**invalid_payload).to_response_payload(request_id="req_12345678")


def test_to_response_payload_requires_non_empty_request_id() -> None:
    error = AppError(
        code=ErrorCode.APPLICATION_API_INPUT_INVALID,
        message="Invalid input.",
        hint="Check request payload and retry.",
    )

    with pytest.raises(ValidationError):
        error.to_response_payload(request_id="  ")


def test_internal_error_requires_explicit_hint() -> None:
    invalid_payload: dict[str, Any] = {"message": "Unexpected internal error."}
    with pytest.raises(TypeError):
        InternalError(**invalid_payload)


def test_internal_error_defaults_code_and_uses_explicit_hint() -> None:
    error = InternalError(
        message="Unexpected internal error.",
        hint="Retry later with the request_id.",
    )

    payload = error.to_response_payload(request_id="req_12345678")
    assert payload.hint == "Retry later with the request_id."
    assert payload.code == ErrorCode.INTERNAL_API_UNEXPECTED_ERROR.value


def test_payload_uses_only_safe_details_not_log_details() -> None:
    error = AppError(
        code=ErrorCode.INFRA_DB_CONNECTION_UNAVAILABLE,
        message="Database unavailable.",
        hint="Retry later.",
        safe_details={"resource": "knowledge-db"},
        log_details={"dsn": "postgresql://internal-secret"},
    )

    payload = error.to_response_payload(request_id="req_12345678")

    assert payload.details == {"resource": "knowledge-db"}
    assert "dsn" not in str(payload)


def test_error_subclasses_keep_same_payload_shape() -> None:
    errors = [
        ApplicationError(
            code=ErrorCode.APPLICATION_API_INPUT_INVALID,
            message="Request validation failed.",
            hint="Fix request parameters and retry.",
        ),
        DomainError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION,
            message="Domain rule violated.",
            hint="Adjust input and retry.",
        ),
        ApplicationError(
            code=ErrorCode.APPLICATION_SEARCH_STATE_CONFLICT,
            message="Application state conflict.",
            hint="Retry with latest state.",
        ),
        InfrastructureError(
            code=ErrorCode.INFRA_DB_CONNECTION_UNAVAILABLE,
            message="Infrastructure unavailable.",
            hint="Retry later.",
        ),
        InternalError(
            code=ErrorCode.INTERNAL_API_UNEXPECTED_ERROR,
            message="Internal error.",
            hint="Retry later with request_id.",
        ),
    ]

    for error in errors:
        payload = error.to_response_payload(request_id="req_12345678")
        assert set(payload.model_dump()) == {
            "code",
            "message",
            "details",
            "hint",
            "request_id",
        }
