#!/usr/bin/env python3
"""
Abstract: Operator CLI for incremental taxonomy classification of unassigned nodes.
Out of scope: HTTP-triggered orchestration and taxonomy tree import behavior.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from entrypoints.runtime import get_runtime_dependencies
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.service import TaxonomyService
from modules.taxonomy_classification.cursor_runner import CursorClassificationRunner
from modules.taxonomy_classification.dto import (
    TaxonomyClassificationBatchResult,
    TaxonomyClassificationNodeOutcome,
)
from modules.taxonomy_classification.service import TaxonomyClassificationService

_ROOT_DIR = Path(__file__).resolve().parents[1]
_SESSION_TOOL_SCRIPT = _ROOT_DIR / "scripts" / "taxonomy-classification-session-tool.py"


class _ProgressState:
    def __init__(self) -> None:
        self.total: int | None = None
        self.completed = 0
        self.assigned = 0
        self.unchanged = 0
        self.errors = 0


def _build_progress_description(state: _ProgressState) -> str:
    if state.total is None:
        return "Selecting unassigned taxonomy nodes..."
    return (
        f"Taxonomy classification progress "
        f"{state.completed}/{state.total} "
        f"(assigned={state.assigned}, unchanged={state.unchanged}, errors={state.errors})"
    )


async def run_taxonomy_classification(
    *,
    limit: int | None,
    max_workers: int | None,
    on_selection_resolved: Callable[[int], None] | None = None,
    on_node_finished: Callable[[TaxonomyClassificationNodeOutcome], None] | None = None,
) -> TaxonomyClassificationBatchResult:
    runtime = get_runtime_dependencies()
    async with runtime.session_factory() as session:
        knowledge_service = build_knowledge_graph_service(
            session=session,
            edge_title_mention_top_k=runtime.settings.edge_title_mention_top_k,
            edge_semantic_top_k=runtime.settings.edge_semantic_top_k,
            edge_semantic_min_strength=runtime.settings.edge_semantic_min_strength,
            edge_semantic_candidate_limit=runtime.settings.edge_semantic_candidate_limit,
        )
        taxonomy_service = TaxonomyService(repo=TaxonomyRepo(session=session))
        runner = CursorClassificationRunner(
            command=runtime.settings.taxonomy_classification_cursor_command,
            workspace_root=Path(
                runtime.settings.taxonomy_classification_cursor_workspace_root
            ),
            timeout_seconds=runtime.settings.taxonomy_classification_cursor_timeout_seconds,
            max_retries=runtime.settings.taxonomy_classification_cursor_max_retries,
            session_tool_script=_SESSION_TOOL_SCRIPT,
        )
        service = TaxonomyClassificationService(
            knowledge_port=knowledge_service,
            cursor_runner=runner,
            taxonomy_status_port=taxonomy_service,
            default_max_workers=runtime.settings.taxonomy_classification_max_workers,
        )
        return await service.classify_unassigned(
            limit=limit,
            max_workers=max_workers,
            on_selection_resolved=on_selection_resolved,
            on_node_finished=on_node_finished,
        )


def _build_summary_table(result: TaxonomyClassificationBatchResult) -> Table:
    table = Table(title="Taxonomy Classification Summary")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    table.add_row("Selected", str(result.selected_count))
    table.add_row("Assigned", str(result.assigned_count))
    table.add_row("Unchanged", str(result.unchanged_count))
    table.add_row("Errors", str(result.error_count))
    return table


@click.command()
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=None,
    help="Process only the first N unassigned nodes ordered by node id.",
)
@click.option(
    "--max-workers",
    type=click.IntRange(min=1),
    default=None,
    help="Override default concurrency for this run.",
)
def cli(limit: int | None, max_workers: int | None) -> None:
    console = Console()
    progress_state = _ProgressState()
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task(
                _build_progress_description(progress_state), total=None
            )

            def _on_selection_resolved(selected_count: int) -> None:
                progress_state.total = selected_count
                progress.update(
                    task_id,
                    total=selected_count,
                    completed=0,
                    description=_build_progress_description(progress_state),
                )

            def _on_node_finished(outcome: TaxonomyClassificationNodeOutcome) -> None:
                progress_state.completed += 1
                if outcome.status == "assigned":
                    progress_state.assigned += 1
                elif outcome.status == "already_assigned":
                    progress_state.unchanged += 1
                else:
                    progress_state.errors += 1
                progress.update(
                    task_id,
                    advance=1,
                    description=_build_progress_description(progress_state),
                )

            result = asyncio.run(
                run_taxonomy_classification(
                    limit=limit,
                    max_workers=max_workers,
                    on_selection_resolved=_on_selection_resolved,
                    on_node_finished=_on_node_finished,
                )
            )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    console.print(_build_summary_table(result))
    if result.error_count > 0:
        console.print(
            f"[yellow]Completed with {result.error_count} node-level errors.[/yellow]"
        )


if __name__ == "__main__":
    cli()
