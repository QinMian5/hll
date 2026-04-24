"""
Abstract: Global app-error primitives and payload conversion for API error
governance.
Out of scope: FastAPI exception-handler registration, HTTP status mapping
policy, and startup wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ErrorCode(StrEnum):
    APPLICATION_API_INPUT_INVALID = "APPLICATION_API_INPUT_INVALID"
    APPLICATION_INGESTION_PAYLOAD_INVALID = "APPLICATION_INGESTION_PAYLOAD_INVALID"
    APPLICATION_INGESTION_STATE_CONFLICT = "APPLICATION_INGESTION_STATE_CONFLICT"
    APPLICATION_TAXONOMY_INPUT_INVALID = "APPLICATION_TAXONOMY_INPUT_INVALID"
    DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND = "DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND"
    DOMAIN_KNOWLEDGE_RULE_VIOLATION = "DOMAIN_KNOWLEDGE_RULE_VIOLATION"
    DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND = "DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND"
    APPLICATION_SEARCH_STATE_CONFLICT = "APPLICATION_SEARCH_STATE_CONFLICT"
    INFRA_DB_CONNECTION_UNAVAILABLE = "INFRA_DB_CONNECTION_UNAVAILABLE"
    INFRA_EMBEDDING_SERVICE_UNAVAILABLE = "INFRA_EMBEDDING_SERVICE_UNAVAILABLE"
    INFRA_QUEUE_UNAVAILABLE = "INFRA_QUEUE_UNAVAILABLE"
    INTERNAL_API_UNEXPECTED_ERROR = "INTERNAL_API_UNEXPECTED_ERROR"


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, use_enum_values=True)

    code: ErrorCode
    message: NonEmptyString
    details: dict[str, Any] = Field(default_factory=dict)
    hint: NonEmptyString
    request_id: NonEmptyString


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    error: ErrorPayload


@dataclass(slots=True, kw_only=True)
class AppError(Exception):
    code: ErrorCode
    message: str
    hint: str
    safe_details: dict[str, Any] = field(default_factory=dict)
    log_details: dict[str, Any] = field(default_factory=dict)

    def to_response_payload(self, *, request_id: str) -> ErrorPayload:
        return ErrorPayload(
            code=self.code,
            message=self.message,
            details=self.safe_details,
            hint=self.hint,
            request_id=request_id,
        )

    def to_response_envelope(self, *, request_id: str) -> ErrorEnvelope:
        return ErrorEnvelope(error=self.to_response_payload(request_id=request_id))

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"


class DomainError(AppError):
    pass


class ApplicationError(AppError):
    pass


class InfrastructureError(AppError):
    pass


class InternalError(AppError):
    def __init__(
        self,
        *,
        code: ErrorCode = ErrorCode.INTERNAL_API_UNEXPECTED_ERROR,
        message: str,
        hint: str,
        safe_details: dict[str, Any] | None = None,
        log_details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            hint=hint,
            safe_details={} if safe_details is None else safe_details,
            log_details={} if log_details is None else log_details,
        )
