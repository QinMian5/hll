"""
Abstract: Table-scope and safety helpers for API production snapshot bootstraps.
Out of scope: Docker command execution, database connectivity, and SQL dump storage.
"""

from __future__ import annotations

from pathlib import Path

import click

API_BOOTSTRAP_TABLES: tuple[str, ...] = (
    "ingestion_requests",
    "nodes",
    "taxonomy_classification_webhook_events",
    "taxonomy_nodes",
    "card_versions",
    "edges",
    "node_taxonomy_assignments",
    "taxonomy_classification_jobs",
    "taxonomy_classification_continuation_requests",
    "taxonomy_classification_webhook_wakeups",
    "adjacency",
    "workspace_roles",
    "card_proposals",
    "proposal_apply_audits",
    "taxonomy_scope_projection_edges",
)


def assert_development_env_file(env_file: Path) -> None:
    if env_file.name != ".env.dev":
        raise ValueError("Dev bootstrap import requires infra/env/.env.dev.")


def build_pg_dump_table_args() -> tuple[str, ...]:
    return tuple(f"--table=public.{table_name}" for table_name in API_BOOTSTRAP_TABLES)


def build_truncate_sql() -> str:
    table_list = ",\n".join(f"  public.{table_name}" for table_name in API_BOOTSTRAP_TABLES)
    return f"TRUNCATE TABLE\n{table_list}\nRESTART IDENTITY CASCADE;\n"


@click.group()
def cli() -> None:
    """Print shell-consumable bootstrap SQL and pg_dump arguments."""


@cli.command("dump-table-args")
def dump_table_args_command() -> None:
    for table_arg in build_pg_dump_table_args():
        click.echo(table_arg)


@cli.command("truncate-sql")
def truncate_sql_command() -> None:
    click.echo(build_truncate_sql(), nl=False)


@cli.command("validate-dev-env")
@click.argument("env_file", type=click.Path(path_type=Path))
def validate_dev_env_command(env_file: Path) -> None:
    try:
        assert_development_env_file(env_file)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
