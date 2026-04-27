"""
Abstract: Integration tests for taxonomy-classification job queue result processing.
Out of scope: Live job-queue-mcp transport and webhook authentication.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from job_queue_mcp_client.types import AcceptedResult as AcceptedTaxonomyClassificationJobResult
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.taxonomy.model import TaxonomyNode
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy_classification.model import (
    TaxonomyClassificationJob,
    TaxonomyClassificationWebhookEvent,
    TaxonomyClassificationWebhookWakeup,
)
from modules.taxonomy_classification.runtime import TaxonomyClassificationRuntimeService
from modules.taxonomy_classification.submission import TaxonomyClassificationSubmissionService
from modules.taxonomy_classification.webhook import (
    TaxonomyClassificationWebhookPayload,
    TaxonomyClassificationWebhookRepository,
)

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


@dataclass(slots=True)
class FakeJobQueueClient:
    results_by_job_id: dict[int, AcceptedTaxonomyClassificationJobResult]
    requested_result_job_ids: list[int] = field(default_factory=list)

    async def get_result(self, job_id: int) -> AcceptedTaxonomyClassificationJobResult:
        self.requested_result_job_ids.append(job_id)
        return self.results_by_job_id[job_id]


@dataclass(slots=True)
class FakeCreateJobClient:
    created_jobs: list[dict[str, Any]] = field(default_factory=list)
    create_job_ids: list[int] = field(default_factory=list)
    on_create: Callable[[Mapping[str, Any]], Awaitable[None]] | None = None

    async def create_job(
        self,
        *,
        queue_name: str,
        instruction: str,
        output_schema: dict[str, object],
        priority: str = "normal",
        payload: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> int:
        created_job = {
            "queue_name": queue_name,
            "priority": priority,
            "instruction": instruction,
            "output_schema": output_schema,
            "payload": payload or {},
            "metadata": metadata or {},
        }
        self.created_jobs.append(created_job)
        if self.on_create is not None:
            await self.on_create(created_job)
        return self.create_job_ids.pop(0)


async def _create_node(db_session: AsyncSession) -> Node:
    node = Node(
        title="Linear Algebra",
        content="Vector spaces.",
        embedding=[0.1] * 1536,
    )
    db_session.add(node)
    await db_session.flush()
    return node


async def _create_taxonomy_tree(
    db_session: AsyncSession,
) -> tuple[TaxonomyNode, TaxonomyNode, TaxonomyNode, TaxonomyNode]:
    root = TaxonomyNode(parent_id=None, name="Root", depth=0, is_leaf=False)
    db_session.add(root)
    await db_session.flush()

    root_unclassified = TaxonomyNode(
        parent_id=root.id,
        name="Unclassified",
        depth=1,
        is_leaf=True,
    )
    science = TaxonomyNode(parent_id=root.id, name="Science", depth=1, is_leaf=False)
    db_session.add_all([root_unclassified, science])
    await db_session.flush()

    science_unclassified = TaxonomyNode(
        parent_id=science.id,
        name="Unclassified",
        depth=2,
        is_leaf=True,
    )
    db_session.add(science_unclassified)
    await db_session.flush()
    return root, root_unclassified, science, science_unclassified


async def _record_event(
    db_session: AsyncSession,
    *,
    event_id: str,
    job_id: int,
) -> None:
    await TaxonomyClassificationWebhookRepository(db_session).record_event(
        TaxonomyClassificationWebhookPayload.model_validate(
            {
                "event_id": event_id,
                "event_type": "result.accepted",
                "job_id": job_id,
                "queue_name": "taxonomy_classification",
                "occurred_at": datetime(2026, 4, 26, 15, 0, tzinfo=UTC),
                "submission_id": job_id + 1000,
            }
        )
    )
    await db_session.commit()


def _accepted_result(
    *,
    job_id: int,
    result_payload: dict[str, Any],
) -> AcceptedTaxonomyClassificationJobResult:
    return AcceptedTaxonomyClassificationJobResult(
        job_id=job_id,
        submission_id=job_id + 1000,
        received_at=datetime(2026, 4, 26, 15, 1, tzinfo=UTC),
        result_payload=result_payload,
    )


async def _count_wakeups(db_session: AsyncSession, *, event_id: str) -> int:
    count = await db_session.scalar(
        select(func.count())
        .select_from(TaxonomyClassificationWebhookWakeup)
        .where(TaxonomyClassificationWebhookWakeup.event_id == event_id)
    )
    return int(count or 0)


async def test_valid_child_result_moves_assignment_to_child_unclassified_leaf(
    db_session: AsyncSession,
) -> None:
    root, root_unclassified, science, science_unclassified = await _create_taxonomy_tree(db_session)
    node = await _create_node(db_session)
    taxonomy_repo = TaxonomyRepo(session=db_session)
    await taxonomy_repo.set_current_assignment(
        node_id=node.id,
        taxonomy_node_id=root_unclassified.id,
    )
    db_session.add(
        TaxonomyClassificationJob(
            scope_node_id=root.id,
            source_unclassified_node_id=root_unclassified.id,
            node_id=node.id,
            job_id=7001,
        )
    )
    await db_session.commit()
    await _record_event(db_session, event_id="evt-valid-child", job_id=7001)

    service = TaxonomyClassificationRuntimeService(
        db_session,
        job_queue_client=FakeJobQueueClient(
            {
                7001: _accepted_result(
                    job_id=7001,
                    result_payload={
                        "target": {
                            "kind": "child",
                            "child_id": science.id,
                            "reason": "The card belongs under Science.",
                        }
                    },
                )
            }
        ),
    )

    processed_count = await service.process_pending_webhook_events(
        now=datetime(2026, 4, 26, 15, 2, tzinfo=UTC)
    )
    await db_session.commit()

    assignment = await taxonomy_repo.get_assignment_for_node(node_id=node.id)
    assert processed_count == 1
    assert assignment is not None
    assert assignment.taxonomy_node.id == science_unclassified.id


async def test_operator_submission_creates_one_job_per_card_in_scope_unclassified(
    db_session: AsyncSession,
) -> None:
    root, root_unclassified, science, _science_unclassified = await _create_taxonomy_tree(
        db_session
    )
    node = await _create_node(db_session)
    await TaxonomyRepo(session=db_session).set_current_assignment(
        node_id=node.id,
        taxonomy_node_id=root_unclassified.id,
    )
    await db_session.commit()
    client = FakeCreateJobClient(create_job_ids=[8001])
    service = TaxonomyClassificationSubmissionService(
        db_session,
        job_queue_client=client,
        queue_name="taxonomy_classification",
    )

    submitted_count = await service.submit_scope_refinement_jobs(
        scope_node_id=root.id,
        limit=None,
    )
    await db_session.commit()
    stored_job = await db_session.scalar(
        select(TaxonomyClassificationJob).where(TaxonomyClassificationJob.job_id == 8001)
    )

    assert submitted_count == 1
    assert stored_job is not None
    assert stored_job.scope_node_id == root.id
    assert stored_job.source_unclassified_node_id == root_unclassified.id
    assert stored_job.node_id == node.id
    assert client.created_jobs[0]["queue_name"] == "taxonomy_classification"
    assert client.created_jobs[0]["metadata"] == {
        "scope_node_id": root.id,
        "source_unclassified_node_id": root_unclassified.id,
        "node_id": node.id,
    }
    payload = client.created_jobs[0]["payload"]
    assert payload["source_unclassified_node"]["id"] == root_unclassified.id
    assert payload["card"]["id"] == node.id
    assert payload["children"] == [{"id": science.id, "name": "Science"}]


async def test_operator_submission_persists_local_intent_before_remote_job_create(
    db_session: AsyncSession,
) -> None:
    root, root_unclassified, _science, _science_unclassified = await _create_taxonomy_tree(
        db_session
    )
    node = await _create_node(db_session)
    await TaxonomyRepo(session=db_session).set_current_assignment(
        node_id=node.id,
        taxonomy_node_id=root_unclassified.id,
    )
    await db_session.commit()

    local_intent_committed = False

    def mark_local_intent_committed(_session: object) -> None:
        nonlocal local_intent_committed
        local_intent_committed = True

    event.listen(db_session.sync_session, "after_commit", mark_local_intent_committed)

    async def assert_pending_local_job(_created_job: Mapping[str, Any]) -> None:
        assert local_intent_committed is True
        pending_job = await db_session.scalar(
            select(TaxonomyClassificationJob)
            .where(TaxonomyClassificationJob.scope_node_id == root.id)
            .where(TaxonomyClassificationJob.source_unclassified_node_id == root_unclassified.id)
            .where(TaxonomyClassificationJob.node_id == node.id)
            .where(TaxonomyClassificationJob.job_id.is_(None))
        )
        assert pending_job is not None

    try:
        client = FakeCreateJobClient(create_job_ids=[8002], on_create=assert_pending_local_job)
        service = TaxonomyClassificationSubmissionService(
            db_session,
            job_queue_client=client,
            queue_name="taxonomy_classification",
        )

        submitted_count = await service.submit_scope_refinement_jobs(
            scope_node_id=root.id,
            limit=None,
        )
    finally:
        event.remove(db_session.sync_session, "after_commit", mark_local_intent_committed)
    await db_session.commit()
    stored_job = await db_session.scalar(
        select(TaxonomyClassificationJob).where(TaxonomyClassificationJob.job_id == 8002)
    )

    assert submitted_count == 1
    assert stored_job is not None
    assert stored_job.node_id == node.id


async def test_operator_submission_reuses_pending_local_intent_without_duplicate_job(
    db_session: AsyncSession,
) -> None:
    root, root_unclassified, _science, _science_unclassified = await _create_taxonomy_tree(
        db_session
    )
    node = await _create_node(db_session)
    await TaxonomyRepo(session=db_session).set_current_assignment(
        node_id=node.id,
        taxonomy_node_id=root_unclassified.id,
    )
    db_session.add(
        TaxonomyClassificationJob(
            scope_node_id=root.id,
            source_unclassified_node_id=root_unclassified.id,
            node_id=node.id,
            job_id=None,
        )
    )
    await db_session.commit()

    client = FakeCreateJobClient(create_job_ids=[8003])
    service = TaxonomyClassificationSubmissionService(
        db_session,
        job_queue_client=client,
        queue_name="taxonomy_classification",
    )

    submitted_count = await service.submit_scope_refinement_jobs(
        scope_node_id=root.id,
        limit=None,
    )
    await db_session.commit()
    stored_jobs_count = await db_session.scalar(
        select(func.count())
        .select_from(TaxonomyClassificationJob)
        .where(TaxonomyClassificationJob.scope_node_id == root.id)
        .where(TaxonomyClassificationJob.source_unclassified_node_id == root_unclassified.id)
        .where(TaxonomyClassificationJob.node_id == node.id)
    )
    stored_job = await db_session.scalar(
        select(TaxonomyClassificationJob).where(TaxonomyClassificationJob.job_id == 8003)
    )

    assert submitted_count == 1
    assert stored_jobs_count == 1
    assert stored_job is not None
    assert stored_job.node_id == node.id


async def test_invalid_child_result_is_terminal_local_error_without_assignment_move(
    db_session: AsyncSession,
) -> None:
    root, root_unclassified, _science, _science_unclassified = await _create_taxonomy_tree(
        db_session
    )
    node = await _create_node(db_session)
    taxonomy_repo = TaxonomyRepo(session=db_session)
    await taxonomy_repo.set_current_assignment(
        node_id=node.id,
        taxonomy_node_id=root_unclassified.id,
    )
    job = TaxonomyClassificationJob(
        scope_node_id=root.id,
        source_unclassified_node_id=root_unclassified.id,
        node_id=node.id,
        job_id=7002,
    )
    db_session.add(job)
    await db_session.commit()
    await _record_event(db_session, event_id="evt-invalid-child", job_id=7002)

    service = TaxonomyClassificationRuntimeService(
        db_session,
        job_queue_client=FakeJobQueueClient(
            {
                7002: _accepted_result(
                    job_id=7002,
                    result_payload={
                        "target": {
                            "kind": "child",
                            "child_id": 999999,
                            "reason": "Bad child id.",
                        }
                    },
                )
            }
        ),
    )

    processed_count = await service.process_pending_webhook_events(
        now=datetime(2026, 4, 26, 15, 2, tzinfo=UTC)
    )
    await db_session.commit()
    await db_session.refresh(job)
    event = await db_session.scalar(
        select(TaxonomyClassificationWebhookEvent).where(
            TaxonomyClassificationWebhookEvent.event_id == "evt-invalid-child"
        )
    )
    assignment = await taxonomy_repo.get_assignment_for_node(node_id=node.id)

    assert processed_count == 1
    assert job.processed_at is not None
    assert "out-of-scope child" in (job.last_error or "")
    assert event is not None
    assert event.processed_at is not None
    assert await _count_wakeups(db_session, event_id="evt-invalid-child") == 0
    assert assignment is not None
    assert assignment.taxonomy_node.id == root_unclassified.id


async def test_processed_keep_unclassified_job_does_not_block_later_submission(
    db_session: AsyncSession,
) -> None:
    root, root_unclassified, _science, _science_unclassified = await _create_taxonomy_tree(
        db_session
    )
    node = await _create_node(db_session)
    processed_job = TaxonomyClassificationJob(
        scope_node_id=root.id,
        source_unclassified_node_id=root_unclassified.id,
        node_id=node.id,
        job_id=7003,
        processed_at=datetime(2026, 4, 26, 15, 2, tzinfo=UTC),
        target_payload={"target": {"kind": "unclassified"}},
    )
    db_session.add(processed_job)
    await db_session.flush()

    db_session.add(
        TaxonomyClassificationJob(
            scope_node_id=root.id,
            source_unclassified_node_id=root_unclassified.id,
            node_id=node.id,
            job_id=7004,
        )
    )
    await db_session.flush()
