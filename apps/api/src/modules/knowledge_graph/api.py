"""
Abstract: FastAPI route contract for private knowledge-graph card suggestion writes.
Out of scope: Browser session ownership and review-workbench actions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, status

from core.errors import DomainError, ErrorCode, ErrorEnvelope
from modules.knowledge_graph.schema import (
    CardProposalCreateRequest,
    CardProposalListResponse,
    CardProposalResponse,
    CardProposalReviewRequest,
    NonEmptyString,
    SuggestedEditCreateRequest,
    SuggestedEditCreateResponse,
)
from modules.knowledge_graph.service import (
    CardProposalInvalidStateError,
    CardProposalNotFoundError,
    CardProposalPermissionError,
    CardProposalValidationError,
    CardSuggestedEditNoChangeError,
    CardVersionNotFoundError,
    KnowledgeGraphService,
)

KnowledgeGraphServiceProvider = Callable[..., KnowledgeGraphService]


def _proposal_response(record: object) -> CardProposalResponse:
    return CardProposalResponse.model_validate(record, from_attributes=True)


def _proposal_error(exc: Exception) -> DomainError:
    if isinstance(exc, CardProposalNotFoundError):
        return DomainError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND,
            message="Card proposal was not found.",
            hint="Refresh the proposal list and retry.",
        )
    if isinstance(exc, CardProposalPermissionError):
        return DomainError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_PERMISSION_DENIED,
            message="Reviewer permission is required for this proposal action.",
            hint="Use a Knowledge reviewer account or request reviewer access.",
        )
    if isinstance(exc, CardProposalInvalidStateError):
        return DomainError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION,
            message="Card proposal is not pending review.",
            hint="Refresh the proposal list and retry.",
        )
    if isinstance(exc, CardProposalValidationError):
        return DomainError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION,
            message=str(exc),
            hint="Fix the proposal fields and retry.",
        )
    if isinstance(exc, CardVersionNotFoundError):
        return DomainError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND,
            message="Card base version was not found.",
            hint="Refresh the card and retry the proposal.",
        )
    if isinstance(exc, CardSuggestedEditNoChangeError):
        return DomainError(
            code=ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION,
            message="Suggested edit must change the card title or content.",
            hint="Change the title or content before submitting.",
        )
    raise exc


def build_router(*, get_knowledge_graph_service: KnowledgeGraphServiceProvider) -> APIRouter:
    router = APIRouter(tags=["knowledge-graph"])

    @router.post(
        "/card-proposals",
        response_model=CardProposalResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ErrorEnvelope},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorEnvelope},
        },
    )
    async def create_card_proposal(
        payload: CardProposalCreateRequest,
        actor_user_id: Annotated[
            NonEmptyString,
            Header(alias="X-Knowledge-Actor-User-Id"),
        ],
        service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    ) -> CardProposalResponse:
        try:
            record = await service.submit_card_proposal(
                proposal_type=payload.proposal_type,
                submitted_by_user_id=actor_user_id,
                proposed_title=payload.proposed_title,
                proposed_content=payload.proposed_content,
                target_node_id=payload.target_node_id,
                base_version=payload.base_version,
                suggested_title=payload.suggested_title,
                suggested_content=payload.suggested_content,
                reason=payload.reason,
            )
        except (
            CardProposalValidationError,
            CardVersionNotFoundError,
            CardSuggestedEditNoChangeError,
        ) as exc:
            raise _proposal_error(exc) from exc

        return _proposal_response(record)

    @router.get(
        "/card-proposals/my",
        response_model=CardProposalListResponse,
    )
    async def list_my_card_proposals(
        actor_user_id: Annotated[
            NonEmptyString,
            Header(alias="X-Knowledge-Actor-User-Id"),
        ],
        service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    ) -> CardProposalListResponse:
        records = await service.list_card_proposals_for_user(user_id=actor_user_id)
        return CardProposalListResponse(
            proposals=[_proposal_response(record) for record in records],
        )

    @router.get(
        "/card-proposals/review-queue",
        response_model=CardProposalListResponse,
        responses={status.HTTP_403_FORBIDDEN: {"model": ErrorEnvelope}},
    )
    async def list_card_proposals_for_review(
        actor_user_id: Annotated[
            NonEmptyString,
            Header(alias="X-Knowledge-Actor-User-Id"),
        ],
        service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    ) -> CardProposalListResponse:
        try:
            records = await service.list_pending_card_proposals_for_review(
                reviewer_user_id=actor_user_id,
            )
        except CardProposalPermissionError as exc:
            raise _proposal_error(exc) from exc
        return CardProposalListResponse(
            proposals=[_proposal_response(record) for record in records],
        )

    @router.post(
        "/card-proposals/{proposal_id}/accept",
        response_model=CardProposalResponse,
        responses={
            status.HTTP_403_FORBIDDEN: {"model": ErrorEnvelope},
            status.HTTP_404_NOT_FOUND: {"model": ErrorEnvelope},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorEnvelope},
        },
    )
    async def accept_card_proposal(
        payload: CardProposalReviewRequest,
        proposal_id: Annotated[int, Path(gt=0)],
        actor_user_id: Annotated[
            NonEmptyString,
            Header(alias="X-Knowledge-Actor-User-Id"),
        ],
        service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    ) -> CardProposalResponse:
        try:
            record = await service.accept_card_proposal(
                proposal_id=proposal_id,
                reviewer_user_id=actor_user_id,
                review_note=payload.review_note,
            )
        except (
            CardProposalInvalidStateError,
            CardProposalNotFoundError,
            CardProposalPermissionError,
            CardProposalValidationError,
        ) as exc:
            raise _proposal_error(exc) from exc
        return _proposal_response(record)

    @router.post(
        "/card-proposals/{proposal_id}/reject",
        response_model=CardProposalResponse,
        responses={
            status.HTTP_403_FORBIDDEN: {"model": ErrorEnvelope},
            status.HTTP_404_NOT_FOUND: {"model": ErrorEnvelope},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorEnvelope},
        },
    )
    async def reject_card_proposal(
        payload: CardProposalReviewRequest,
        proposal_id: Annotated[int, Path(gt=0)],
        actor_user_id: Annotated[
            NonEmptyString,
            Header(alias="X-Knowledge-Actor-User-Id"),
        ],
        service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    ) -> CardProposalResponse:
        try:
            record = await service.reject_card_proposal(
                proposal_id=proposal_id,
                reviewer_user_id=actor_user_id,
                review_note=payload.review_note,
            )
        except (
            CardProposalInvalidStateError,
            CardProposalNotFoundError,
            CardProposalPermissionError,
        ) as exc:
            raise _proposal_error(exc) from exc
        return _proposal_response(record)

    @router.post(
        "/card-proposals/{proposal_id}/withdraw",
        response_model=CardProposalResponse,
        responses={
            status.HTTP_403_FORBIDDEN: {"model": ErrorEnvelope},
            status.HTTP_404_NOT_FOUND: {"model": ErrorEnvelope},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorEnvelope},
        },
    )
    async def withdraw_card_proposal(
        proposal_id: Annotated[int, Path(gt=0)],
        actor_user_id: Annotated[
            NonEmptyString,
            Header(alias="X-Knowledge-Actor-User-Id"),
        ],
        service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    ) -> CardProposalResponse:
        try:
            record = await service.withdraw_card_proposal(
                proposal_id=proposal_id,
                user_id=actor_user_id,
            )
        except (
            CardProposalInvalidStateError,
            CardProposalNotFoundError,
            CardProposalPermissionError,
        ) as exc:
            raise _proposal_error(exc) from exc
        return _proposal_response(record)

    @router.post(
        "/cards/{node_id}/suggested-edits",
        response_model=SuggestedEditCreateResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ErrorEnvelope},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorEnvelope},
        },
    )
    async def create_suggested_edit(
        payload: SuggestedEditCreateRequest,
        node_id: Annotated[int, Path(gt=0)],
        suggested_by_user_id: Annotated[
            NonEmptyString,
            Header(alias="X-Knowledge-Suggested-By-User-Id"),
        ],
        service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
    ) -> SuggestedEditCreateResponse:
        try:
            record = await service.submit_card_suggested_edit(
                node_id=node_id,
                base_version=payload.base_version,
                suggested_title=payload.suggested_title,
                suggested_content=payload.suggested_content,
                suggested_by_user_id=suggested_by_user_id,
            )
        except CardVersionNotFoundError as exc:
            raise DomainError(
                code=ErrorCode.DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND,
                message="Card base version was not found.",
                hint="Refresh the card and retry the suggestion.",
                safe_details={"node_id": node_id, "base_version": payload.base_version},
            ) from exc
        except CardSuggestedEditNoChangeError as exc:
            raise DomainError(
                code=ErrorCode.DOMAIN_KNOWLEDGE_RULE_VIOLATION,
                message="Suggested edit must change the card title or content.",
                hint="Change the title or content before submitting.",
            ) from exc

        return SuggestedEditCreateResponse(
            id=record.id,
            node_id=record.node_id,
            base_version=record.base_version,
            status=record.status,
            created_at=record.created_at,
        )

    return router
