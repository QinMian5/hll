#!/usr/bin/env python3
"""
Abstract: Session-scoped taxonomy tool commands for Cursor progressive classification.
Out of scope: Batch node selection and Cursor subprocess orchestration.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import click

from entrypoints.runtime import get_runtime_dependencies
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.service import TaxonomyService
from modules.taxonomy_classification.session_tool import (
    TaxonomyClassificationSessionTool,
)


async def _with_tool[ResultT](
    *,
    operation: Callable[[TaxonomyClassificationSessionTool], Awaitable[ResultT]],
) -> ResultT:
    runtime = get_runtime_dependencies()
    async with runtime.session_factory() as session:
        taxonomy_service = TaxonomyService(repo=TaxonomyRepo(session=session))
        tool = TaxonomyClassificationSessionTool(taxonomy_port=taxonomy_service)
        return await operation(tool)


@click.group()
def cli() -> None:
    pass


@cli.command("list-children")
@click.option(
    "--parent-id",
    type=click.IntRange(min=1),
    default=None,
    help="Parent taxonomy node id. Omit for root children.",
)
def list_children_command(parent_id: int | None) -> None:
    async def _operation(tool: TaxonomyClassificationSessionTool) -> str:
        response = await tool.list_children(parent_id=parent_id)
        return response.model_dump_json()

    try:
        click.echo(asyncio.run(_with_tool(operation=_operation)))
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command("get-assignment")
@click.option(
    "--node-id",
    required=True,
    type=click.IntRange(min=1),
    help="Knowledge node id.",
)
def get_assignment_command(node_id: int) -> None:
    async def _operation(tool: TaxonomyClassificationSessionTool) -> str:
        response = await tool.get_assignment(node_id=node_id)
        return response.model_dump_json()

    try:
        click.echo(asyncio.run(_with_tool(operation=_operation)))
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command("assign-taxonomy-node")
@click.option(
    "--node-id",
    required=True,
    type=click.IntRange(min=1),
    help="Knowledge node id.",
)
@click.option(
    "--taxonomy-node-id",
    required=True,
    type=click.IntRange(min=1),
    help="Taxonomy node id.",
)
def assign_taxonomy_node_command(node_id: int, taxonomy_node_id: int) -> None:
    async def _operation(tool: TaxonomyClassificationSessionTool) -> str:
        response = await tool.assign_taxonomy_node(
            node_id=node_id,
            taxonomy_node_id=taxonomy_node_id,
        )
        return response.model_dump_json()

    try:
        click.echo(asyncio.run(_with_tool(operation=_operation)))
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
