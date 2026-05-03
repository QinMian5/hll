"""
Abstract: HTTP-layer status mapping and validation-error normalization for app
errors.
Out of scope: FastAPI route registration and domain-specific service rules.
"""

from __future__ import annotations

from fastapi.exceptions import RequestValidationError

from core.errors import AppError, ApplicationError, ErrorCode

LAYOUT_NOT_READY_RETRY_AFTER_SECONDS = 10

_STATUS_BY_ERROR_CODE: dict[ErrorCode, int] = {
    ErrorCode.APPLICATION_API_INPUT_INVALID: 422,
    ErrorCode.APPLICATION_INGESTION_PAYLOAD_INVALID: 400,
    ErrorCode.APPLICATION_INGESTION_STATE_CONFLICT: 409,
    ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID: 400,
    ErrorCode.APPLICATION_TAXONOMY_LAYOUT_NOT_READY: 503,
    ErrorCode.APPLICATION_SEARCH_STATE_CONFLICT: 409,
    ErrorCode.DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND: 404,
    ErrorCode.DOMAIN_KNOWLEDGE_PERMISSION_DENIED: 403,
    ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION: 422,
    ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND: 404,
    ErrorCode.INFRA_DB_CONNECTION_UNAVAILABLE: 503,
    ErrorCode.INFRA_EMBEDDING_SERVICE_UNAVAILABLE: 503,
    ErrorCode.INFRA_QUEUE_UNAVAILABLE: 503,
    ErrorCode.INTERNAL_API_UNEXPECTED_ERROR: 500,
}


def status_code_for_app_error(error: AppError) -> int:
    return _STATUS_BY_ERROR_CODE.get(error.code, 500)


def headers_for_app_error(error: AppError) -> dict[str, str]:
    if error.code is ErrorCode.APPLICATION_TAXONOMY_LAYOUT_NOT_READY:
        return {"Retry-After": str(LAYOUT_NOT_READY_RETRY_AFTER_SECONDS)}
    return {}


def app_error_from_request_validation(_exc: RequestValidationError) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.APPLICATION_API_INPUT_INVALID,
        message="Request validation failed.",
        hint="Fix request parameters or payload fields and retry.",
    )
