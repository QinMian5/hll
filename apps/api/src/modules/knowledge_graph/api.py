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
    NonEmptyString,
    SuggestedEditCreateRequest,
    SuggestedEditCreateResponse,
)
from modules.knowledge_graph.service import (
    CardSuggestedEditNoChangeError,
    CardVersionNotFoundError,
    KnowledgeGraphService,
)

KnowledgeGraphServiceProvider = Callable[..., KnowledgeGraphService]


def build_router(*, get_knowledge_graph_service: KnowledgeGraphServiceProvider) -> APIRouter:
    router = APIRouter(tags=["knowledge-graph"])

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
