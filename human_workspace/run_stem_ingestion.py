"""
Abstract: Run fixed STEM page ingestion from corpus selection through page orchestration.
Out of scope: Runtime tuning flags, domain filtering, and benchmark reporting.
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_CORPUS_SRC = PROJECT_ROOT / "apps" / "knowledge_corpus" / "src"
HUMAN_WORKSPACE_DIR = PROJECT_ROOT / "human_workspace"
if str(KNOWLEDGE_CORPUS_SRC) not in sys.path:
    sys.path.insert(0, str(KNOWLEDGE_CORPUS_SRC))
if str(HUMAN_WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(HUMAN_WORKSPACE_DIR))

from wiki_page_to_cards_orchestrator import run_pages
from wiki_page_to_cards_types import PageRecord, PageResult
from wiki_stem_page_candidates import build_stem_page_records

MAX_WORKERS = 8


def main() -> None:
    console = Console()
    pages = build_stem_page_records()
    total = len(pages)

    if total == 0:
        console.print("No STEM pages matched the configured seed titles.")
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TextColumn("last: {task.fields[last_title]}"),
        console=console,
        transient=False,
    )

    def on_page_finished(page: PageRecord, result: PageResult) -> None:
        progress.update(task_id, advance=1, last_title=page.title)

    with progress:
        task_id = progress.add_task(
            "Running STEM page ingestion",
            total=total,
            last_title="",
        )
        run_pages(
            pages,
            max_workers=MAX_WORKERS,
            on_page_finished=on_page_finished,
        )

    console.print(f"Finished processing {total} STEM pages.")


if __name__ == "__main__":
    main()
