"""
Abstract: Submit Pageviews-selected Wikipedia pages into source-pipeline intake.
Out of scope: Pageviews selection, worker execution, and card-level review results.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION_JSONL = (
    PROJECT_ROOT
    / "human_workspace"
    / "pageview-selection-output"
    / "selected_pageview_candidates.jsonl"
)


@dataclass(frozen=True, slots=True)
class PageviewCandidate:
    selection_rank: int
    page_id: int
    title: str
    url: str
    total_views: int
    months_seen: int
    best_rank: int
    score: int
    text_length: int


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    page_id: int
    title: str
    url: str
    clean_text: str


@dataclass(frozen=True, slots=True)
class SubmissionPlan:
    units_to_insert: list[dict[str, Any]]
    page_ids_to_mark_processed: set[int]
    skipped_existing_source_refs: set[str]
    skipped_processed_page_ids: set[int]


class MissingCorpusDocumentsError(RuntimeError):
    pass


def source_ref_for_page_id(page_id: int) -> str:
    return f"wikipedia:{page_id}"


def external_target_ref_for_page_id(page_id: int) -> str:
    return f"source-pipeline:wikipedia:{page_id}"


def load_pageview_candidates(path: Path) -> list[PageviewCandidate]:
    candidates: list[PageviewCandidate] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
                candidates.append(
                    PageviewCandidate(
                        selection_rank=int(payload["selection_rank"]),
                        page_id=int(payload["page_id"]),
                        title=str(payload["title"]),
                        url=str(payload["url"]),
                        total_views=int(payload["total_views"]),
                        months_seen=int(payload["months_seen"]),
                        best_rank=int(payload["best_rank"]),
                        score=int(payload["score"]),
                        text_length=int(payload["text_length"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid candidate at {path}:{line_number}") from exc
    return candidates


def build_source_unit(
    candidate: PageviewCandidate,
    document: CorpusDocument,
    *,
    selection_name: str,
) -> dict[str, Any]:
    return {
        "source_kind": "wikipedia",
        "source_ref": source_ref_for_page_id(candidate.page_id),
        "title": document.title,
        "content": document.clean_text,
        "metadata": {
            "page_id": candidate.page_id,
            "url": document.url,
            "selection_batch": selection_name,
            "selection_rank": candidate.selection_rank,
            "pageview_total_views": candidate.total_views,
            "pageview_months_seen": candidate.months_seen,
            "pageview_best_rank": candidate.best_rank,
            "pageview_score": candidate.score,
            "selected_title": candidate.title,
            "selected_url": candidate.url,
            "selected_text_length": candidate.text_length,
        },
    }


def plan_submission(
    candidates: list[PageviewCandidate],
    *,
    documents: dict[int, CorpusDocument],
    existing_source_refs: set[str],
    processed_page_ids: set[int],
    selection_name: str,
) -> SubmissionPlan:
    candidate_page_ids = {candidate.page_id for candidate in candidates}
    missing_page_ids = sorted(candidate_page_ids - documents.keys())
    if missing_page_ids:
        sample = ", ".join(str(page_id) for page_id in missing_page_ids[:20])
        raise MissingCorpusDocumentsError(
            f"selected pages are missing from corpus documents: {sample}"
        )

    units_to_insert: list[dict[str, Any]] = []
    page_ids_to_mark_processed: set[int] = set()
    skipped_existing_source_refs: set[str] = set()
    skipped_processed_page_ids: set[int] = set()

    for candidate in candidates:
        source_ref = source_ref_for_page_id(candidate.page_id)
        if candidate.page_id in processed_page_ids:
            skipped_processed_page_ids.add(candidate.page_id)
            continue
        if source_ref in existing_source_refs:
            skipped_existing_source_refs.add(source_ref)
            page_ids_to_mark_processed.add(candidate.page_id)
            continue

        document = documents[candidate.page_id]
        units_to_insert.append(
            build_source_unit(candidate, document, selection_name=selection_name)
        )
        page_ids_to_mark_processed.add(candidate.page_id)

    return SubmissionPlan(
        units_to_insert=units_to_insert,
        page_ids_to_mark_processed=page_ids_to_mark_processed,
        skipped_existing_source_refs=skipped_existing_source_refs,
        skipped_processed_page_ids=skipped_processed_page_ids,
    )


def build_run_config_payload(
    *,
    selection_jsonl: Path,
    selection_name: str,
    input_count: int,
    units_to_insert_count: int,
    skipped_existing_source_ref_count: int,
    skipped_processed_count: int,
) -> dict[str, Any]:
    return {
        "source": "pageviews-top-selection",
        "selection_name": selection_name,
        "selection_jsonl": str(selection_jsonl),
        "input_count": input_count,
        "selected_unit_count": units_to_insert_count,
        "skipped_existing_source_ref_count": skipped_existing_source_ref_count,
        "skipped_processed_count": skipped_processed_count,
    }


def load_corpus_documents_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    page_ids: set[int],
) -> dict[int, CorpusDocument]:
    if not page_ids:
        return {}

    sql = f"""
CREATE TEMP TABLE selected_page_ids(page_id bigint primary key);
COPY selected_page_ids(page_id) FROM STDIN WITH (FORMAT csv);
{_copy_csv_payload([[page_id] for page_id in sorted(page_ids)])}\\.
SELECT json_build_object(
    'page_id', d.page_id,
    'title', d.title,
    'url', d.url,
    'clean_text', d.clean_text
)::text
FROM wikipedia.documents d
JOIN selected_page_ids s ON s.page_id = d.page_id
ORDER BY s.page_id;
"""
    stdout = run_psql_script(
        container=container,
        postgres_user=postgres_user,
        postgres_db=postgres_db,
        sql=sql,
    )
    documents: dict[int, CorpusDocument] = {}
    for payload in _iter_json_payloads(stdout):
        document = CorpusDocument(
            page_id=int(payload["page_id"]),
            title=str(payload["title"]),
            url=str(payload["url"]),
            clean_text=str(payload["clean_text"]),
        )
        documents[document.page_id] = document
    return documents


def load_processed_page_ids_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    page_ids: set[int],
) -> set[int]:
    if not page_ids:
        return set()

    sql = f"""
CREATE TEMP TABLE selected_page_ids(page_id bigint primary key);
COPY selected_page_ids(page_id) FROM STDIN WITH (FORMAT csv);
{_copy_csv_payload([[page_id] for page_id in sorted(page_ids)])}\\.
SELECT p.page_id
FROM wikipedia.processed_documents p
JOIN selected_page_ids s ON s.page_id = p.page_id
ORDER BY p.page_id;
"""
    stdout = run_psql_script(
        container=container,
        postgres_user=postgres_user,
        postgres_db=postgres_db,
        sql=sql,
    )
    return {int(line) for line in stdout.splitlines() if line.strip().isdigit()}


def load_existing_source_refs_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    source_refs: set[str],
) -> set[str]:
    if not source_refs:
        return set()

    sql = f"""
CREATE TEMP TABLE selected_source_refs(source_ref text primary key);
COPY selected_source_refs(source_ref) FROM STDIN WITH (FORMAT csv);
{_copy_csv_payload([[source_ref] for source_ref in sorted(source_refs)])}\\.
SELECT u.source_ref
FROM workflow_units u
JOIN selected_source_refs s ON s.source_ref = u.source_ref
ORDER BY u.source_ref;
"""
    stdout = run_psql_script(
        container=container,
        postgres_user=postgres_user,
        postgres_db=postgres_db,
        sql=sql,
    )
    return {line.strip() for line in stdout.splitlines() if line.strip()}


def insert_source_pipeline_run_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    units: list[dict[str, Any]],
    config_payload: dict[str, Any],
) -> int | None:
    if not units:
        return None

    sql = f"""
BEGIN;
CREATE TEMP TABLE run_config(payload jsonb) ON COMMIT DROP;
COPY run_config(payload) FROM STDIN WITH (FORMAT csv);
{_copy_csv_payload([[json.dumps(config_payload, ensure_ascii=False, sort_keys=True)]])}\\.
CREATE TEMP TABLE unit_payloads(payload jsonb) ON COMMIT DROP;
COPY unit_payloads(payload) FROM STDIN WITH (FORMAT csv);
{_copy_csv_payload([[json.dumps(unit, ensure_ascii=False, sort_keys=True)] for unit in units])}\\.
WITH new_run AS (
    INSERT INTO workflow_runs(source_kind, config_payload)
    SELECT 'wikipedia', payload::json
    FROM run_config
    RETURNING id
),
inserted_units AS (
    INSERT INTO workflow_units(workflow_run_id, source_kind, source_ref, payload)
    SELECT
        new_run.id,
        unit_payloads.payload ->> 'source_kind',
        unit_payloads.payload ->> 'source_ref',
        unit_payloads.payload::json
    FROM unit_payloads
    CROSS JOIN new_run
    RETURNING id
)
SELECT json_build_object(
    'workflow_run_id', (SELECT id FROM new_run),
    'unit_count', (SELECT count(*) FROM inserted_units)
)::text;
COMMIT;
"""
    stdout = run_psql_script(
        container=container,
        postgres_user=postgres_user,
        postgres_db=postgres_db,
        sql=sql,
    )
    payloads = list(_iter_json_payloads(stdout))
    if not payloads:
        raise RuntimeError("source_pipeline insertion did not return a workflow_run_id")
    payload = payloads[-1]
    inserted_count = int(payload["unit_count"])
    if inserted_count != len(units):
        raise RuntimeError(f"inserted {inserted_count} units, expected {len(units)}")
    return int(payload["workflow_run_id"])


def mark_processed_documents_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    page_ids: set[int],
) -> int:
    if not page_ids:
        return 0

    sql = f"""
CREATE TEMP TABLE selected_page_ids(page_id bigint primary key);
COPY selected_page_ids(page_id) FROM STDIN WITH (FORMAT csv);
{_copy_csv_payload([[page_id] for page_id in sorted(page_ids)])}\\.
WITH upserted AS (
    INSERT INTO wikipedia.processed_documents(page_id, external_target_ref)
    SELECT page_id, 'source-pipeline:wikipedia:' || page_id::text
    FROM selected_page_ids
    ON CONFLICT (page_id) DO UPDATE
    SET external_target_ref = EXCLUDED.external_target_ref
    RETURNING page_id
)
SELECT count(*) FROM upserted;
"""
    stdout = run_psql_script(
        container=container,
        postgres_user=postgres_user,
        postgres_db=postgres_db,
        sql=sql,
    )
    counts = [int(line) for line in stdout.splitlines() if line.strip().isdigit()]
    if not counts:
        raise RuntimeError("processed marker upsert did not return a count")
    return counts[-1]


def count_units_without_page_to_card_jobs_from_docker(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    workflow_run_id: int,
) -> int:
    sql = (
        "SELECT count(*) FROM workflow_units "
        f"WHERE workflow_run_id = {int(workflow_run_id)} "
        "AND page_to_card_job_id IS NULL;"
    )
    stdout = run_psql_script(
        container=container,
        postgres_user=postgres_user,
        postgres_db=postgres_db,
        sql=sql,
    )
    counts = [int(line) for line in stdout.splitlines() if line.strip().isdigit()]
    if not counts:
        raise RuntimeError("page_to_card job count query returned no count")
    return counts[-1]


def wait_for_page_to_card_jobs(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    workflow_run_id: int,
    timeout_seconds: int,
    poll_interval_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = count_units_without_page_to_card_jobs_from_docker(
            container=container,
            postgres_user=postgres_user,
            postgres_db=postgres_db,
            workflow_run_id=workflow_run_id,
        )
        print(
            f"workflow_run_id={workflow_run_id} units_without_page_to_card_job={remaining}",
            file=sys.stderr,
            flush=True,
        )
        if remaining == 0:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for page_to_card jobs; {remaining} units remain")
        time.sleep(poll_interval_seconds)


def run_psql_script(
    *,
    container: str,
    postgres_user: str,
    postgres_db: str,
    sql: str,
) -> str:
    command = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-U",
        postgres_user,
        "-d",
        postgres_db,
        "-v",
        "ON_ERROR_STOP=1",
        "-q",
        "-t",
        "-A",
    ]
    completed = subprocess.run(
        command,
        input=sql,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"psql failed in {container}/{postgres_db}: {completed.stderr.strip()}")
    return completed.stdout


def _copy_csv_payload(rows: list[list[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return buffer.getvalue()


def _iter_json_payloads(stdout: str) -> Iterator[dict[str, Any]]:
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("{"):
            yield json.loads(stripped)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit Pageviews-selected Wikipedia pages to source_pipeline."
    )
    parser.add_argument("--selection-jsonl", type=Path, default=DEFAULT_SELECTION_JSONL)
    parser.add_argument("--selection-name", default="pageviews-top-2024-05-to-2026-04")
    parser.add_argument("--submit", action="store_true", help="Write prod DB state.")
    parser.add_argument(
        "--wait-for-page-jobs",
        action="store_true",
        help="After submit, wait until the orchestrator creates page_to_card jobs.",
    )
    parser.add_argument("--wait-timeout-seconds", type=int, default=600)
    parser.add_argument("--wait-poll-interval-seconds", type=float, default=5.0)
    parser.add_argument("--corpus-container", default="knowledge-prod-knowledge_corpus_db-1")
    parser.add_argument("--corpus-user", default="knowledge_corpus_admin")
    parser.add_argument("--corpus-db", default="knowledge_corpus")
    parser.add_argument(
        "--source-pipeline-container",
        default="knowledge-prod-source_pipeline_db-1",
    )
    parser.add_argument("--source-pipeline-user", default="source_pipeline_admin")
    parser.add_argument("--source-pipeline-db", default="source_pipeline")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = load_pageview_candidates(args.selection_jsonl)
    page_ids = {candidate.page_id for candidate in candidates}
    source_refs = {source_ref_for_page_id(page_id) for page_id in page_ids}

    documents = load_corpus_documents_from_docker(
        container=args.corpus_container,
        postgres_user=args.corpus_user,
        postgres_db=args.corpus_db,
        page_ids=page_ids,
    )
    processed_page_ids = load_processed_page_ids_from_docker(
        container=args.corpus_container,
        postgres_user=args.corpus_user,
        postgres_db=args.corpus_db,
        page_ids=page_ids,
    )
    existing_source_refs = load_existing_source_refs_from_docker(
        container=args.source_pipeline_container,
        postgres_user=args.source_pipeline_user,
        postgres_db=args.source_pipeline_db,
        source_refs=source_refs,
    )
    plan = plan_submission(
        candidates,
        documents=documents,
        existing_source_refs=existing_source_refs,
        processed_page_ids=processed_page_ids,
        selection_name=args.selection_name,
    )
    config_payload = build_run_config_payload(
        selection_jsonl=args.selection_jsonl,
        selection_name=args.selection_name,
        input_count=len(candidates),
        units_to_insert_count=len(plan.units_to_insert),
        skipped_existing_source_ref_count=len(plan.skipped_existing_source_refs),
        skipped_processed_count=len(plan.skipped_processed_page_ids),
    )

    mode = "submit" if args.submit else "dry-run"
    print(
        json.dumps(
            {
                "mode": mode,
                "input_candidates": len(candidates),
                "corpus_documents_loaded": len(documents),
                "units_to_insert": len(plan.units_to_insert),
                "page_ids_to_mark_processed": len(plan.page_ids_to_mark_processed),
                "skipped_existing_source_refs": len(plan.skipped_existing_source_refs),
                "skipped_processed_page_ids": len(plan.skipped_processed_page_ids),
            },
            sort_keys=True,
        )
    )

    if not args.submit:
        return

    workflow_run_id = insert_source_pipeline_run_from_docker(
        container=args.source_pipeline_container,
        postgres_user=args.source_pipeline_user,
        postgres_db=args.source_pipeline_db,
        units=plan.units_to_insert,
        config_payload=config_payload,
    )
    marked_count = mark_processed_documents_from_docker(
        container=args.corpus_container,
        postgres_user=args.corpus_user,
        postgres_db=args.corpus_db,
        page_ids=plan.page_ids_to_mark_processed,
    )
    print(
        json.dumps(
            {
                "workflow_run_id": workflow_run_id,
                "inserted_units": len(plan.units_to_insert),
                "processed_marked": marked_count,
            },
            sort_keys=True,
        )
    )

    if args.wait_for_page_jobs and workflow_run_id is not None:
        wait_for_page_to_card_jobs(
            container=args.source_pipeline_container,
            postgres_user=args.source_pipeline_user,
            postgres_db=args.source_pipeline_db,
            workflow_run_id=workflow_run_id,
            timeout_seconds=args.wait_timeout_seconds,
            poll_interval_seconds=args.wait_poll_interval_seconds,
        )


if __name__ == "__main__":
    main()
