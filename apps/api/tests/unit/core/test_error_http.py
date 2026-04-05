"""
Abstract: Unit tests for HTTP status mapping and validation-error normalization.
Out of scope: FastAPI route wiring and module-specific business behavior.
"""

from __future__ import annotations

import pytest
from fastapi.exceptions import RequestValidationError

from core.error_http import app_error_from_request_validation, status_code_for_app_error
from core.errors import (
    AppError,
    ApplicationError,
    DomainError,
    ErrorCode,
    InfrastructureError,
    InternalError,
)


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (
            ApplicationError(
                code=ErrorCode.APPLICATION_API_INPUT_INVALID,
                message="Request validation failed.",
                hint="Fix request parameters and retry.",
            ),
            422,
        ),
        (
            ApplicationError(
                code=ErrorCode.APPLICATION_SEMANTIC_MAP_INPUT_INVALID,
                message="Semantic-map tile request is invalid.",
                hint="Use a supported semantic level and non-negative tile coordinates.",
            ),
            400,
        ),
        (
            DomainError(
                code=ErrorCode.DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND,
                message="Semantic-map snapshot is unavailable.",
                hint="Run a semantic-map build and retry.",
            ),
            404,
        ),
        (
            InfrastructureError(
                code=ErrorCode.INFRA_DB_CONNECTION_UNAVAILABLE,
                message="Database unavailable.",
                hint="Retry later.",
            ),
            503,
        ),
        (
            InternalError(
                message="Unexpected internal error.",
                hint="Retry later with request_id.",
            ),
            500,
        ),
    ],
)
def test_status_code_mapping_is_explicit_and_stable(
    error: AppError,
    expected_status: int,
) -> None:
    assert status_code_for_app_error(error) == expected_status


def test_every_error_code_has_http_status_mapping() -> None:
    for code in ErrorCode:
        error = AppError(
            code=code,
            message="Synthetic error for mapping coverage.",
            hint="Synthetic hint.",
        )
        assert (
            status_code_for_app_error(error) != 500
            or code is ErrorCode.INTERNAL_API_UNEXPECTED_ERROR
        )


def test_request_validation_is_normalized_to_application_api_input_invalid() -> None:
    validation_error = RequestValidationError([])

    error = app_error_from_request_validation(validation_error)

    assert error.code is ErrorCode.APPLICATION_API_INPUT_INVALID
