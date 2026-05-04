"""
Abstract: Submit science-oriented Wikipedia corpus pages into source-pipeline intake.
Out of scope: Cursor page sessions, corpus processed markers, and direct job queue writes.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from knowledge_corpus.config import load_settings as load_corpus_settings
from knowledge_corpus.db.session import build_session_factory as build_corpus_session_factory
from knowledge_corpus.wikipedia.search import search_documents
from knowledge_corpus.wikipedia.types import WikipediaSearchResult
from source_pipeline.db.models import WorkflowUnit
from source_pipeline.db.session import build_engine as build_source_pipeline_engine
from source_pipeline.page_to_card.contracts import SourceUnit
from source_pipeline.pipeline_intake.service import PipelineIntakeService

OPERATOR_TOOLS_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = (
    OPERATOR_TOOLS_ROOT / "assets" / "source_pipeline" / "science-query-batches.yaml"
)
DEFAULT_STATEMENT_TIMEOUT_MS = 10_000


@dataclass(slots=True, frozen=True)
class CorpusPageRecord:
    page_id: int
    url: str
    title: str
    clean_text: str


class ScienceQueryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    query: str = Field(min_length=1)
    limit: int = Field(gt=0)


class ScienceQueryBatchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batches: list[ScienceQueryBatch] = Field(min_length=1)


@dataclass(slots=True, frozen=True)
class PageSelection:
    page: CorpusPageRecord
    batch_name: str
    rank: float


@dataclass(slots=True, frozen=True)
class IntakeSummary:
    submitted: bool
    workflow_run_id: int | None
    unit_count: int


class ExistingWorkflowUnitsError(RuntimeError):
    pass


class SourcePipelineSubmissionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOURCE_PIPELINE_",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str | None = None


type SessionFactory = Callable[[], AsyncSession]


def load_source_pipeline_submission_settings() -> SourcePipelineSubmissionSettings:
    return SourcePipelineSubmissionSettings.model_validate(
        EnvSettingsSource(SourcePipelineSubmissionSettings)()
    )


def load_science_query_batches(path: Path = DEFAULT_CONFIG_PATH) -> ScienceQueryBatchConfig:
    raw = load_science_query_batch_payload(path.read_text(encoding="utf-8"))
    return ScienceQueryBatchConfig.model_validate(raw)


def load_science_query_batch_payload(text: str) -> dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError:
        return parse_science_query_batch_yaml_subset(text)

    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("science query batch config must be a mapping")
    return raw


def parse_science_query_batch_yaml_subset(text: str) -> dict[str, Any]:
    batches: list[dict[str, Any]] = []
    current_batch: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "batches:":
            continue

        if line.startswith("- "):
            if current_batch is not None:
                batches.append(current_batch)
            current_batch = {}
            line = line[2:].strip()
            if not line:
                continue

        if current_batch is None:
            raise ValueError("batch entries must appear under batches")

        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"invalid science query batch line: {raw_line}")

        normalized_value: str | int = value.strip()
        if key.strip() == "limit":
            normalized_value = int(normalized_value)
        current_batch[key.strip()] = normalized_value

    if current_batch is not None:
        batches.append(current_batch)

    return {"batches": batches}


def page_record_from_search_result(result: WikipediaSearchResult) -> CorpusPageRecord:
    return CorpusPageRecord(
        page_id=result.page_id,
        url=result.url,
        title=result.title,
        clean_text=result.clean_text,
    )


def dedupe_page_selections(selections: list[PageSelection]) -> list[PageSelection]:
    selections_by_page_id: dict[int, PageSelection] = {}
    ordered_page_ids: list[int] = []

    for selection in selections:
        page_id = selection.page.page_id
        if page_id not in selections_by_page_id:
            ordered_page_ids.append(page_id)
        selections_by_page_id[page_id] = selection

    return [selections_by_page_id[page_id] for page_id in ordered_page_ids]


def build_source_unit(selection: PageSelection) -> dict[str, Any]:
    page = selection.page
    unit = SourceUnit(
        source_kind="wikipedia",
        source_ref=f"wikipedia:{page.page_id}",
        title=page.title,
        content=page.clean_text,
        metadata={
            "page_id": page.page_id,
            "url": page.url,
            "selection_batch": selection.batch_name,
            "selection_rank": selection.rank,
        },
    )
    return unit.model_dump(mode="json")


async def build_science_page_selections(
    config: ScienceQueryBatchConfig,
    *,
    statement_timeout_ms: int = DEFAULT_STATEMENT_TIMEOUT_MS,
) -> list[PageSelection]:
    settings = load_corpus_settings()
    engine, session_factory = build_corpus_session_factory(settings)
    try:
        selections: list[PageSelection] = []
        async with session_factory() as session:
            await session.execute(text(f"SET statement_timeout = {int(statement_timeout_ms)}"))
            for batch in config.batches:
                results = await search_documents(
                    session,
                    query=batch.query,
                    exclude_processed=True,
                    limit=batch.limit,
                )
                selections.extend(
                    PageSelection(
                        page=page_record_from_search_result(result),
                        batch_name=batch.name,
                        rank=result.rank,
                    )
                    for result in results
                )
        return dedupe_page_selections(selections)
    finally:
        await engine.dispose()


def ensure_no_existing_source_refs(existing_refs: set[str]) -> None:
    if not existing_refs:
        return

    sample = ", ".join(sorted(existing_refs)[:10])
    raise ExistingWorkflowUnitsError(
        f"source_pipeline already contains workflow units for source refs: {sample}"
    )


async def fetch_existing_source_refs(
    session: AsyncSession,
    *,
    source_refs: set[str],
) -> set[str]:
    if not source_refs:
        return set()

    rows = await session.scalars(
        select(WorkflowUnit.source_ref).where(WorkflowUnit.source_ref.in_(source_refs))
    )
    return set(rows)


async def materialize_intake(
    *,
    units: list[dict[str, Any]],
    config_payload: dict[str, Any],
    submit: bool,
    session_factory: SessionFactory,
) -> IntakeSummary:
    if not submit:
        return IntakeSummary(submitted=False, workflow_run_id=None, unit_count=len(units))

    async with session_factory() as session:
        source_refs = {str(unit["source_ref"]) for unit in units}
        ensure_no_existing_source_refs(
            await fetch_existing_source_refs(session, source_refs=source_refs)
        )
        run = await PipelineIntakeService(session).create_run(
            source_kind="wikipedia",
            config_payload={**config_payload, "units": units},
        )
        return IntakeSummary(submitted=True, workflow_run_id=run.id, unit_count=len(units))


def build_config_payload(
    *,
    config_path: Path,
    config: ScienceQueryBatchConfig,
    selected_unit_count: int,
) -> dict[str, Any]:
    return {
        "source": "science-query-batches",
        "config_path": str(config_path),
        "selected_unit_count": selected_unit_count,
        "batches": [batch.model_dump(mode="json") for batch in config.batches],
    }


def build_source_pipeline_session_factory(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = build_source_pipeline_engine(database_url=database_url)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit configured science Wikipedia pages to source_pipeline intake."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--submit", action="store_true", help="Create a source_pipeline run.")
    parser.add_argument(
        "--statement-timeout-ms",
        type=int,
        default=DEFAULT_STATEMENT_TIMEOUT_MS,
    )
    parser.add_argument(
        "--source-pipeline-database-url",
        default=None,
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    config = load_science_query_batches(args.config)
    selections = await build_science_page_selections(
        config,
        statement_timeout_ms=args.statement_timeout_ms,
    )
    units = [build_source_unit(selection) for selection in selections]
    config_payload = build_config_payload(
        config_path=args.config,
        config=config,
        selected_unit_count=len(units),
    )

    if args.submit:
        source_pipeline_database_url = (
            args.source_pipeline_database_url
            or load_source_pipeline_submission_settings().database_url
        )
        if not source_pipeline_database_url:
            raise RuntimeError(
                "SOURCE_PIPELINE_DATABASE_URL or --source-pipeline-database-url is required."
            )
        engine, session_factory = build_source_pipeline_session_factory(
            source_pipeline_database_url
        )
        try:
            summary = await materialize_intake(
                units=units,
                config_payload=config_payload,
                submit=True,
                session_factory=session_factory,
            )
        finally:
            await engine.dispose()
    else:
        summary = await materialize_intake(
            units=units,
            config_payload=config_payload,
            submit=False,
            session_factory=_dry_run_session_factory,
        )

    mode = "submitted" if summary.submitted else "dry-run"
    print(f"{mode}: units={summary.unit_count} workflow_run_id={summary.workflow_run_id}")
    for unit in units[:5]:
        print(f"sample: {unit['source_ref']} {unit['title']}")


def main() -> None:
    asyncio.run(async_main())


def _dry_run_session_factory() -> AsyncSession:
    raise RuntimeError("dry-run must not open source_pipeline")


if __name__ == "__main__":
    main()
