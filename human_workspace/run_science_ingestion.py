"""
Abstract: Run fixed science query-batch ingestion from corpus search through page orchestration.
Out of scope: Runtime tuning flags, ad hoc query editing, and benchmark reporting.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml
from pydantic import Field
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_CORPUS_SRC = PROJECT_ROOT / "apps" / "knowledge_corpus" / "src"
HUMAN_WORKSPACE_DIR = PROJECT_ROOT / "human_workspace"
if str(KNOWLEDGE_CORPUS_SRC) not in sys.path:
    sys.path.insert(0, str(KNOWLEDGE_CORPUS_SRC))
if str(HUMAN_WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(HUMAN_WORKSPACE_DIR))

from knowledge_corpus.config import load_settings
from knowledge_corpus.db.session import build_session_factory
from knowledge_corpus.wikipedia.search import search_documents
from knowledge_corpus.wikipedia.types import WikipediaSearchResult
from wiki_page_to_cards_orchestrator import run_pages
from wiki_page_to_cards_types import PageRecord, PageResult, StrictModel

MAX_WORKERS = 8
DEFAULT_CONFIG_PATH = HUMAN_WORKSPACE_DIR / "science-query-batches.yaml"


class ScienceQueryBatch(StrictModel):
    name: str = Field(description="Human-readable batch name.")
    query: str = Field(description="Full-text query passed to the corpus search helper.")
    limit: int = Field(gt=0, description="Maximum number of pages returned for this batch.")


class ScienceQueryBatchConfig(StrictModel):
    batches: list[ScienceQueryBatch] = Field(
        min_length=1,
        description="Ordered science-oriented search batches.",
    )


def load_science_query_batches(path: Path = DEFAULT_CONFIG_PATH) -> ScienceQueryBatchConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ScienceQueryBatchConfig.model_validate(raw)


def dedupe_page_records(pages: list[PageRecord]) -> list[PageRecord]:
    pages_by_id: dict[int, PageRecord] = {}
    ordered_page_ids: list[int] = []

    for page in pages:
        if page.page_id not in pages_by_id:
            ordered_page_ids.append(page.page_id)
        pages_by_id[page.page_id] = page

    return [pages_by_id[page_id] for page_id in ordered_page_ids]


def _page_record_from_search_result(result: WikipediaSearchResult) -> PageRecord:
    return PageRecord(
        page_id=result.page_id,
        url=result.url,
        title=result.title,
        clean_text=result.clean_text,
    )


async def _build_science_page_records_async(
    config: ScienceQueryBatchConfig,
) -> list[PageRecord]:
    settings = load_settings()
    engine, session_factory = build_session_factory(settings)
    try:
        merged_pages: list[PageRecord] = []
        async with session_factory() as session:
            for batch in config.batches:
                results = await search_documents(
                    session,
                    query=batch.query,
                    exclude_processed=True,
                    limit=batch.limit,
                )
                merged_pages.extend(
                    _page_record_from_search_result(result) for result in results
                )
        return dedupe_page_records(merged_pages)
    finally:
        await engine.dispose()


def build_science_page_records(
    path: Path = DEFAULT_CONFIG_PATH,
) -> list[PageRecord]:
    config = load_science_query_batches(path)
    return asyncio.run(_build_science_page_records_async(config))


def main() -> None:
    console = Console()
    pages = build_science_page_records()
    total = len(pages)

    if total == 0:
        console.print("No science pages matched the configured query batches.")
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("ETA"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )

    def on_page_finished(page: PageRecord, result: PageResult) -> None:
        progress.update(task_id, advance=1)

    with progress:
        task_id = progress.add_task(
            "Running science page ingestion",
            total=total,
        )
        run_pages(
            pages,
            max_workers=MAX_WORKERS,
            on_page_finished=on_page_finished,
        )

    console.print(f"Finished processing {total} science pages.")


if __name__ == "__main__":
    main()
