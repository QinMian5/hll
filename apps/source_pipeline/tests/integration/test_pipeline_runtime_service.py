"""
Abstract: Integration tests for the source-pipeline runtime tick flow.
Out of scope: Process bootstrap and Docker/Compose image wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source_pipeline.card_review.contracts import ReviewItem, ReviewResult
from source_pipeline.db.models import CardReviewJob, WorkflowRun, WorkflowUnit
from source_pipeline.page_to_card.contracts import CardDraft
from source_pipeline.pipeline_runtime.job_queue_client import AcceptedJobResult, NotReadyJobResult
from source_pipeline.pipeline_runtime.service import PipelineRuntimeService

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


@dataclass
class FakeJobQueueClient:
    created_jobs: list[dict[str, object]] = field(default_factory=list)
    create_job_ids: list[int] = field(default_factory=list)
    results_by_job_id: dict[int, AcceptedJobResult | NotReadyJobResult] = field(
        default_factory=dict
    )

    async def create_job(self, **kwargs: object) -> int:
        self.created_jobs.append(kwargs)
        return self.create_job_ids.pop(0)

    async def get_result(self, *, job_id: int) -> AcceptedJobResult | NotReadyJobResult:
        return self.results_by_job_id[job_id]


@dataclass
class FakeReviewHandoff:
    calls: list[dict[str, object]] = field(default_factory=list)

    async def handoff(
        self,
        *,
        workflow_unit_id: int,
        ordinal: int,
        card: CardDraft,
        review: ReviewResult,
    ) -> None:
        self.calls.append(
            {
                "workflow_unit_id": workflow_unit_id,
                "ordinal": ordinal,
                "card": card,
                "review": review,
            }
        )


def build_page_result(*cards: tuple[str, str]) -> AcceptedJobResult:
    return AcceptedJobResult(
        job_id=12,
        submission_id=1,
        received_at=datetime(2026, 4, 20, 23, 0, tzinfo=UTC),
        result_payload={
            "cards": [{"title": title, "content": content} for title, content in cards],
        },
    )


def build_review_result(*, job_id: int) -> AcceptedJobResult:
    return AcceptedJobResult(
        job_id=job_id,
        submission_id=1,
        received_at=datetime(2026, 4, 20, 23, 1, tzinfo=UTC),
        result_payload=ReviewResult(
            title_validity=ReviewItem(passed=True, reason=None),
            title_content_alignment=ReviewItem(passed=True, reason=None),
            title_style_validity=ReviewItem(passed=True, reason=None),
            content_coherence=ReviewItem(passed=True, reason=None),
            content_atomicity=ReviewItem(passed=True, reason=None),
            content_latex_validity=ReviewItem(passed=True, reason=None),
        ).model_dump(mode="json"),
    )


async def create_workflow_unit(db_session: AsyncSession) -> WorkflowUnit:
    run = WorkflowRun(
        source_kind="external",
        config_payload={"units": []},
    )
    db_session.add(run)
    await db_session.flush()

    unit = WorkflowUnit(
        workflow_run_id=run.id,
        source_kind="external",
        source_ref="page-1",
        payload={
            "source_kind": "external",
            "source_ref": "page-1",
            "title": "Page 1",
            "content": "Body",
            "metadata": {},
        },
    )
    db_session.add(unit)
    await db_session.commit()
    return unit


async def test_tick_submits_page_to_card_when_job_id_missing(db_session: AsyncSession) -> None:
    unit = await create_workflow_unit(db_session)
    client = FakeJobQueueClient(create_job_ids=[12])
    handoff = FakeReviewHandoff()
    service = PipelineRuntimeService(db_session, job_queue_client=client, review_handoff=handoff)

    await service.tick()
    await db_session.refresh(unit)

    assert unit.page_to_card_job_id == 12


async def test_tick_rereads_page_to_card_result_and_fans_out_reviews(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    await db_session.commit()

    client = FakeJobQueueClient(
        create_job_ids=[21, 22],
        results_by_job_id={12: build_page_result(("Card A", "A body"), ("Card B", "B body"))},
    )
    handoff = FakeReviewHandoff()
    service = PipelineRuntimeService(db_session, job_queue_client=client, review_handoff=handoff)

    await service.tick()

    review_jobs = list(
        (
            await db_session.execute(
                select(CardReviewJob)
                .where(CardReviewJob.workflow_unit_id == unit.id)
                .order_by(CardReviewJob.ordinal)
            )
        ).scalars()
    )

    assert [job.ordinal for job in review_jobs] == [0, 1]
    assert [job.job_queue_job_id for job in review_jobs] == [21, 22]


async def test_tick_marks_handoff_done_without_persisting_review_payload(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    await db_session.flush()
    review_job = CardReviewJob(
        workflow_unit_id=unit.id,
        ordinal=0,
        job_queue_job_id=21,
        handoff_done=False,
    )
    db_session.add(review_job)
    await db_session.commit()

    client = FakeJobQueueClient(
        results_by_job_id={
            12: build_page_result(("Card A", "A body")),
            21: build_review_result(job_id=21),
        }
    )
    handoff = FakeReviewHandoff()
    service = PipelineRuntimeService(db_session, job_queue_client=client, review_handoff=handoff)

    await service.tick()
    await db_session.refresh(review_job)

    assert review_job.handoff_done is True
    assert len(handoff.calls) == 1
    assert "result_payload" not in CardReviewJob.__table__.c
