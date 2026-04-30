"""
Abstract: Integration tests for the source-pipeline runtime tick flow.
Out of scope: Process bootstrap and Docker/Compose image wiring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from job_queue_mcp_client.errors import ResultNotReadyError
from job_queue_mcp_client.types import AcceptedResult as AcceptedJobResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source_pipeline.card_repair.contracts import CardRepairInput
from source_pipeline.card_repair.instruction import build_card_repair_instruction
from source_pipeline.card_review.contracts import ReviewResult
from source_pipeline.card_review.instruction import build_card_review_instruction
from source_pipeline.db.models import CardCandidate, WorkflowRun, WorkflowUnit
from source_pipeline.page_to_card.contracts import CardDraft
from source_pipeline.page_to_card.instruction import build_page_to_card_instruction
from source_pipeline.pipeline_runtime.service import PipelineRuntimeService
from source_pipeline.pipeline_webhook.contracts import JobQueueWebhookPayload
from source_pipeline.pipeline_webhook.repository import JobQueueWebhookEventRepository

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


@dataclass
class FakeJobQueueClient:
    created_jobs: list[dict[str, object]] = field(default_factory=list)
    create_job_ids: list[int] = field(default_factory=list)
    requested_result_job_ids: list[int] = field(default_factory=list)
    results_by_job_id: dict[int, AcceptedJobResult | Exception] = field(default_factory=dict)

    async def create_job(self, **kwargs: object) -> int:
        self.created_jobs.append(kwargs)
        return self.create_job_ids.pop(0)

    async def get_result(self, job_id: int) -> AcceptedJobResult:
        self.requested_result_job_ids.append(job_id)
        result = self.results_by_job_id[job_id]
        if isinstance(result, Exception):
            raise result
        return result


@dataclass
class FakeAcceptedCardHandoff:
    calls: list[dict[str, object]] = field(default_factory=list)

    async def handoff(
        self,
        *,
        candidate_id: int,
        card: CardDraft,
    ) -> None:
        self.calls.append({"candidate_id": candidate_id, "card": card})


def build_page_result(*cards: tuple[str, str], job_id: int = 12) -> AcceptedJobResult:
    return AcceptedJobResult(
        job_id=job_id,
        submission_id=1,
        received_at=datetime(2026, 4, 20, 23, 0, tzinfo=UTC),
        result_payload={
            "cards": [{"title": title, "content": content} for title, content in cards],
        },
    )


def build_review_result(*, job_id: int, passed: bool = True) -> AcceptedJobResult:
    return AcceptedJobResult(
        job_id=job_id,
        submission_id=1,
        received_at=datetime(2026, 4, 20, 23, 1, tzinfo=UTC),
        result_payload=ReviewResult(
            passed=passed,
            reason=None if passed else "The card does not satisfy the quality standard.",
        ).model_dump(mode="json"),
    )


def build_repair_result(*cards: tuple[str, str], job_id: int = 31) -> AcceptedJobResult:
    return AcceptedJobResult(
        job_id=job_id,
        submission_id=1,
        received_at=datetime(2026, 4, 20, 23, 2, tzinfo=UTC),
        result_payload={
            "cards": [{"title": title, "content": content} for title, content in cards],
        },
    )


def not_ready(*, job_id: int, state: str = "RUNNING") -> ResultNotReadyError:
    return ResultNotReadyError(job_id=job_id, state=state)


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


async def list_candidates(db_session: AsyncSession, unit: WorkflowUnit) -> list[CardCandidate]:
    return list(
        (
            await db_session.execute(
                select(CardCandidate)
                .where(CardCandidate.workflow_unit_id == unit.id)
                .order_by(CardCandidate.id)
            )
        ).scalars()
    )


async def record_webhook_event(
    db_session: AsyncSession,
    *,
    job_id: int,
    event_id: str | None = None,
    event_type: str = "result.accepted",
) -> None:
    await JobQueueWebhookEventRepository(db_session).record_event(
        JobQueueWebhookPayload.model_validate(
            {
                "event_id": event_id or f"evt-{job_id}-{event_type}",
                "event_type": event_type,
                "job_id": job_id,
                "queue_name": "source-pipeline",
                "occurred_at": datetime(2026, 4, 25, 15, 1, tzinfo=UTC),
                "submission_id": job_id + 100 if event_type == "result.accepted" else None,
                "terminal_state": "DEAD_LETTER"
                if event_type == "job.terminal_non_accepted"
                else None,
            }
        )
    )
    await db_session.commit()


async def test_tick_submits_page_to_card_when_job_id_missing(db_session: AsyncSession) -> None:
    unit = await create_workflow_unit(db_session)
    client = FakeJobQueueClient(create_job_ids=[12])
    handoff = FakeAcceptedCardHandoff()
    service = PipelineRuntimeService(db_session, job_queue_client=client, card_handoff=handoff)

    await service.tick()
    await db_session.refresh(unit)

    assert unit.page_to_card_job_id == 12
    assert client.created_jobs[0]["queue_name"] == "page_to_card"
    assert client.created_jobs[0]["instruction"] == build_page_to_card_instruction()
    assert client.created_jobs[0]["metadata"] == {"workflow_unit_id": unit.id}


async def test_tick_limits_units_processed_per_batch(db_session: AsyncSession) -> None:
    for _ in range(3):
        await create_workflow_unit(db_session)

    client = FakeJobQueueClient(create_job_ids=[12, 13, 14])
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
        poll_batch_size=2,
    )

    await service.tick()

    units = list(
        (await db_session.execute(select(WorkflowUnit).order_by(WorkflowUnit.id))).scalars()
    )
    assert [unit.page_to_card_job_id for unit in units] == [12, 13, None]
    assert len(client.created_jobs) == 2


async def test_tick_batch_limit_does_not_starve_later_unsubmitted_units(
    db_session: AsyncSession,
) -> None:
    for _ in range(3):
        await create_workflow_unit(db_session)
    units = list(
        (await db_session.execute(select(WorkflowUnit).order_by(WorkflowUnit.id))).scalars()
    )
    units[0].page_to_card_job_id = 101
    units[1].page_to_card_job_id = 102
    await db_session.commit()

    client = FakeJobQueueClient(
        create_job_ids=[201],
        results_by_job_id={
            101: not_ready(job_id=101),
            102: not_ready(job_id=102),
        },
    )
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
        poll_batch_size=1,
    )

    await service.tick()
    await db_session.refresh(units[2])

    assert units[2].page_to_card_job_id == 201
    assert len(client.created_jobs) == 1


async def test_tick_prioritizes_missing_page_jobs_before_result_polling(
    db_session: AsyncSession,
) -> None:
    for _ in range(2):
        await create_workflow_unit(db_session)
    units = list(
        (await db_session.execute(select(WorkflowUnit).order_by(WorkflowUnit.id))).scalars()
    )
    units[0].page_to_card_job_id = 101
    await db_session.commit()

    client = FakeJobQueueClient(
        create_job_ids=[201],
        results_by_job_id={101: not_ready(job_id=101)},
    )
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
        poll_batch_size=1,
    )

    await service.tick()
    await db_session.refresh(units[1])

    assert units[1].page_to_card_job_id == 201
    assert client.requested_result_job_ids == []


async def test_tick_without_webhook_event_does_not_poll_outstanding_jobs(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    await db_session.commit()
    client = FakeJobQueueClient(results_by_job_id={12: build_page_result(("Card A", "A body"))})
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
    )

    await service.tick()

    assert client.requested_result_job_ids == []
    assert await list_candidates(db_session, unit) == []


async def test_tick_creates_candidates_and_review_jobs_from_page_result(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    await db_session.commit()
    await record_webhook_event(db_session, job_id=12)

    client = FakeJobQueueClient(
        create_job_ids=[21, 22],
        results_by_job_id={
            12: build_page_result(("Card A", "A body"), ("Card B", "B body")),
            21: not_ready(job_id=21),
            22: not_ready(job_id=22),
        },
    )
    handoff = FakeAcceptedCardHandoff()
    service = PipelineRuntimeService(db_session, job_queue_client=client, card_handoff=handoff)

    await service.tick()
    await service.tick()

    candidates = await list_candidates(db_session, unit)
    assert [candidate.origin_ordinal for candidate in candidates] == [0, 1]
    assert [candidate.card_payload["title"] for candidate in candidates] == ["Card A", "Card B"]
    assert [candidate.review_job_id for candidate in candidates] == [21, 22]
    assert [job["queue_name"] for job in client.created_jobs] == ["card_review", "card_review"]
    assert [job["instruction"] for job in client.created_jobs] == [
        build_card_review_instruction(),
        build_card_review_instruction(),
    ]


async def test_tick_with_empty_page_cards_creates_no_candidates_or_review_jobs(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    await db_session.commit()
    await record_webhook_event(db_session, job_id=12)
    client = FakeJobQueueClient(results_by_job_id={12: build_page_result()})
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
    )

    await service.tick()

    assert await list_candidates(db_session, unit) == []
    assert client.created_jobs == []


async def test_tick_hands_off_passed_review_and_marks_candidate_done(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    candidate = CardCandidate(
        workflow_unit_id=unit.id,
        card_payload={"title": "Card A", "content": "A body"},
        origin_step="page_to_card",
        origin_job_id=12,
        origin_ordinal=0,
        review_job_id=21,
    )
    db_session.add(candidate)
    await db_session.commit()
    await record_webhook_event(db_session, job_id=21)

    client = FakeJobQueueClient(
        results_by_job_id={
            21: build_review_result(job_id=21, passed=True),
        }
    )
    handoff = FakeAcceptedCardHandoff()
    service = PipelineRuntimeService(db_session, job_queue_client=client, card_handoff=handoff)

    await service.tick()
    await db_session.refresh(candidate)

    assert candidate.ingestion_handoff_done is True
    assert handoff.calls == [
        {
            "candidate_id": candidate.id,
            "card": CardDraft(title="Card A", content="A body"),
        }
    ]
    assert "result_payload" not in CardCandidate.__table__.c


async def test_tick_submits_repair_job_for_failed_review_once(db_session: AsyncSession) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    candidate = CardCandidate(
        workflow_unit_id=unit.id,
        card_payload={"title": "bad title", "content": "A body"},
        origin_step="page_to_card",
        origin_job_id=12,
        origin_ordinal=0,
        review_job_id=21,
    )
    db_session.add(candidate)
    await db_session.commit()
    await record_webhook_event(db_session, job_id=21)

    client = FakeJobQueueClient(
        create_job_ids=[31],
        results_by_job_id={
            21: build_review_result(job_id=21, passed=False),
            31: not_ready(job_id=31),
        },
    )
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
    )

    await service.tick()
    await service.tick()
    await db_session.refresh(candidate)

    assert candidate.repair_job_id == 31
    assert [job["queue_name"] for job in client.created_jobs] == ["card_repair"]
    assert client.created_jobs[0]["instruction"] == build_card_repair_instruction()
    repair_input = CardRepairInput.model_validate(client.created_jobs[0]["payload"])
    assert repair_input.card.title == "bad title"
    assert repair_input.review.passed is False


async def test_tick_repair_empty_cards_stops_lineage(db_session: AsyncSession) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    candidate = CardCandidate(
        workflow_unit_id=unit.id,
        card_payload={"title": "bad title", "content": "A body"},
        origin_step="page_to_card",
        origin_job_id=12,
        origin_ordinal=0,
        review_job_id=21,
        repair_job_id=31,
    )
    db_session.add(candidate)
    await db_session.commit()
    await record_webhook_event(db_session, job_id=31)

    client = FakeJobQueueClient(
        results_by_job_id={
            31: build_repair_result(),
        }
    )
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
    )

    await service.tick()

    assert [candidate.id for candidate in await list_candidates(db_session, unit)] == [candidate.id]


async def test_tick_repair_cards_create_child_candidates_that_reenter_review(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    candidate = CardCandidate(
        workflow_unit_id=unit.id,
        card_payload={"title": "bad title", "content": "A body"},
        origin_step="page_to_card",
        origin_job_id=12,
        origin_ordinal=0,
        review_job_id=21,
        repair_job_id=31,
    )
    db_session.add(candidate)
    await db_session.commit()
    await record_webhook_event(db_session, job_id=31)

    client = FakeJobQueueClient(
        create_job_ids=[41, 42],
        results_by_job_id={
            31: build_repair_result(("Card A", "A body"), ("Card B", "B body")),
            41: not_ready(job_id=41),
            42: not_ready(job_id=42),
        },
    )
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
    )

    await service.tick()
    await service.tick()
    await service.tick()

    candidates = await list_candidates(db_session, unit)
    assert [item.parent_candidate_id for item in candidates] == [None, candidate.id, candidate.id]
    assert [item.card_payload["title"] for item in candidates] == ["bad title", "Card A", "Card B"]
    assert [item.review_job_id for item in candidates[1:]] == [41, 42]
    assert [job["queue_name"] for job in client.created_jobs] == ["card_review", "card_review"]


async def test_terminal_non_accepted_page_result_stops_fanout(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    await db_session.commit()
    await record_webhook_event(
        db_session,
        job_id=12,
        event_type="job.terminal_non_accepted",
    )
    client = FakeJobQueueClient()
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
    )

    await service.tick()
    await db_session.refresh(unit)

    assert await list_candidates(db_session, unit) == []
    assert getattr(unit, "page_to_card_terminal_state", None) == "DEAD_LETTER"
    assert client.created_jobs == []

    await service.tick()

    assert client.requested_result_job_ids == []


async def test_terminal_non_accepted_review_result_stops_repair_and_handoff(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    candidate = CardCandidate(
        workflow_unit_id=unit.id,
        card_payload={"title": "Card A", "content": "A body"},
        origin_step="page_to_card",
        origin_job_id=12,
        origin_ordinal=0,
        review_job_id=21,
    )
    db_session.add(candidate)
    await db_session.commit()
    await record_webhook_event(
        db_session,
        job_id=21,
        event_type="job.terminal_non_accepted",
    )
    handoff = FakeAcceptedCardHandoff()
    client = FakeJobQueueClient()
    service = PipelineRuntimeService(db_session, job_queue_client=client, card_handoff=handoff)

    await service.tick()
    await db_session.refresh(candidate)

    assert getattr(candidate, "review_terminal_state", None) == "DEAD_LETTER"
    assert candidate.repair_job_id is None
    assert candidate.ingestion_handoff_done is False
    assert handoff.calls == []

    await service.tick()

    assert client.requested_result_job_ids.count(21) == 0


async def test_terminal_non_accepted_repair_result_stops_child_candidate_creation(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    candidate = CardCandidate(
        workflow_unit_id=unit.id,
        card_payload={"title": "bad title", "content": "A body"},
        origin_step="page_to_card",
        origin_job_id=12,
        origin_ordinal=0,
        review_job_id=21,
        repair_job_id=31,
    )
    db_session.add(candidate)
    await db_session.commit()
    await record_webhook_event(
        db_session,
        job_id=31,
        event_type="job.terminal_non_accepted",
    )
    client = FakeJobQueueClient()
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
    )

    await service.tick()
    await db_session.refresh(candidate)

    assert getattr(candidate, "repair_terminal_state", None) == "DEAD_LETTER"
    assert [candidate.id for candidate in await list_candidates(db_session, unit)] == [candidate.id]

    await service.tick()

    assert client.requested_result_job_ids.count(31) == 0


async def test_low_frequency_reconcile_polls_outstanding_jobs_only_after_interval(
    db_session: AsyncSession,
) -> None:
    unit = await create_workflow_unit(db_session)
    unit.page_to_card_job_id = 12
    await db_session.commit()
    now_values = [
        datetime(2026, 4, 25, 15, 0, tzinfo=UTC),
        datetime(2026, 4, 25, 15, 1, tzinfo=UTC),
        datetime(2026, 4, 25, 16, 1, tzinfo=UTC),
    ]

    def clock() -> datetime:
        return now_values.pop(0)

    client = FakeJobQueueClient(
        create_job_ids=[21],
        results_by_job_id={12: build_page_result(("Card A", "A body"))},
    )
    service = PipelineRuntimeService(
        db_session,
        job_queue_client=client,
        card_handoff=FakeAcceptedCardHandoff(),
        reconcile_interval_seconds=3600,
        reconcile_batch_size=1,
        clock=clock,
    )

    await service.tick()
    await service.tick()
    assert client.requested_result_job_ids == []

    await service.tick()

    assert client.requested_result_job_ids == [12]
    candidates = await list_candidates(db_session, unit)
    assert [candidate.card_payload["title"] for candidate in candidates] == ["Card A"]
    assert [candidate.review_job_id for candidate in candidates] == [21]
