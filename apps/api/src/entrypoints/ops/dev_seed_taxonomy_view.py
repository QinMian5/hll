"""
Abstract: Development-only placeholder data seed for taxonomy GraphView.
Out of scope: Production taxonomy import, embedding generation, and migration execution.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import click
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from entrypoints.runtime import get_runtime_dependencies
from modules.knowledge_graph.model import Adjacency, Edge, Node
from modules.knowledge_graph.repo import KnowledgeRepo
from modules.taxonomy.model import (
    NodeTaxonomyAssignment,
    TaxonomyLeafProjectionEdge,
    TaxonomyNode,
)

DEV_ROOT_NAME = "Root"
DEV_SEED_BRANCHES: dict[str, tuple[str, ...]] = {
    "Branch1": ("Leaf1", "Leaf2"),
    "Branch2": ("Leaf3", "Leaf4"),
}
DEV_SEED_EMBEDDING_DIMENSIONS = 1536


@dataclass(slots=True, frozen=True)
class DevSeedCardSpec:
    title: str
    content: str
    leaf_name: str


@dataclass(slots=True, frozen=True)
class DevSeedEdgeSpec:
    left_title: str
    right_title: str
    strength: float


@dataclass(slots=True, frozen=True)
class DevSeedResult:
    root_id: int
    taxonomy_node_count: int
    card_count: int
    edge_count: int
    projection_edge_count: int


DEV_SEED_CARD_SPECS: tuple[DevSeedCardSpec, ...] = (
    DevSeedCardSpec("Card1", "Placeholder content for Card1.", "Leaf1"),
    DevSeedCardSpec("Card2", "Placeholder content for Card2.", "Leaf1"),
    DevSeedCardSpec("Card3", "Placeholder content for Card3.", "Leaf2"),
    DevSeedCardSpec("Card4", "Placeholder content for Card4.", "Leaf2"),
    DevSeedCardSpec("Card5", "Placeholder content for Card5.", "Leaf3"),
    DevSeedCardSpec("Card6", "Placeholder content for Card6.", "Leaf3"),
    DevSeedCardSpec("Card7", "Placeholder content for Card7.", "Leaf4"),
    DevSeedCardSpec("Card8", "Placeholder content for Card8.", "Leaf4"),
)
DEV_SEED_EDGE_SPECS: tuple[DevSeedEdgeSpec, ...] = (
    DevSeedEdgeSpec("Card1", "Card2", 0.95),
    DevSeedEdgeSpec("Card2", "Card3", 0.82),
    DevSeedEdgeSpec("Card3", "Card4", 0.91),
    DevSeedEdgeSpec("Card4", "Card5", 0.74),
    DevSeedEdgeSpec("Card5", "Card6", 0.89),
    DevSeedEdgeSpec("Card6", "Card7", 0.78),
    DevSeedEdgeSpec("Card7", "Card8", 0.93),
    DevSeedEdgeSpec("Card1", "Card8", 0.66),
    DevSeedEdgeSpec("Card2", "Card6", 0.71),
)


def assert_development_database_url(database_url: str) -> None:
    url = make_url(database_url)
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Dev taxonomy seed requires a local development database URL.")


async def seed_dev_taxonomy_view(
    *,
    session: AsyncSession,
    reset: bool,
) -> DevSeedResult:
    if reset:
        await _delete_existing_dev_seed(session=session)
    elif await _has_existing_dev_seed(session=session):
        raise ValueError("Dev taxonomy seed rows already exist. Re-run with --reset.")

    root = await _get_or_create_root(session=session)
    leaf_ids_by_name = await _create_taxonomy_seed(session=session, root_id=root.id)
    node_ids_by_title = await _create_card_seed(session=session)
    await _create_assignment_seed(
        session=session,
        leaf_ids_by_name=leaf_ids_by_name,
        node_ids_by_title=node_ids_by_title,
    )
    edge_endpoints_by_id = await _create_edge_seed(
        session=session,
        node_ids_by_title=node_ids_by_title,
    )
    projection_edge_count = await _create_leaf_projection_seed(
        session=session,
        edge_endpoints_by_id=edge_endpoints_by_id,
        leaf_ids_by_name=leaf_ids_by_name,
        node_ids_by_title=node_ids_by_title,
    )
    await session.commit()
    return DevSeedResult(
        root_id=root.id,
        taxonomy_node_count=1
        + len(DEV_SEED_BRANCHES)
        + sum(len(leaves) for leaves in DEV_SEED_BRANCHES.values()),
        card_count=len(DEV_SEED_CARD_SPECS),
        edge_count=len(DEV_SEED_EDGE_SPECS),
        projection_edge_count=projection_edge_count,
    )


async def run_seed(*, reset: bool) -> DevSeedResult:
    runtime = get_runtime_dependencies()
    assert_development_database_url(runtime.settings.database_url)
    async with runtime.session_factory() as session:
        try:
            return await seed_dev_taxonomy_view(session=session, reset=reset)
        except Exception:
            await session.rollback()
            raise


async def _has_existing_dev_seed(*, session: AsyncSession) -> bool:
    card_titles = [card.title for card in DEV_SEED_CARD_SPECS]
    existing_card_id = await session.scalar(select(Node.id).where(Node.title.in_(card_titles)))
    if existing_card_id is not None:
        return True

    root = await _get_root(session=session)
    if root is None:
        return False
    branch_names = list(DEV_SEED_BRANCHES)
    existing_branch_id = await session.scalar(
        select(TaxonomyNode.id)
        .where(TaxonomyNode.parent_id == root.id)
        .where(TaxonomyNode.name.in_(branch_names))
    )
    return existing_branch_id is not None


async def _delete_existing_dev_seed(*, session: AsyncSession) -> None:
    card_titles = [card.title for card in DEV_SEED_CARD_SPECS]
    await session.execute(delete(Node).where(Node.title.in_(card_titles)))

    root = await _get_root(session=session)
    if root is None:
        await session.flush()
        return

    branch_ids = (
        await session.scalars(
            select(TaxonomyNode.id)
            .where(TaxonomyNode.parent_id == root.id)
            .where(TaxonomyNode.name.in_(list(DEV_SEED_BRANCHES)))
        )
    ).all()
    if not branch_ids:
        await session.flush()
        return

    leaf_ids = (
        await session.scalars(select(TaxonomyNode.id).where(TaxonomyNode.parent_id.in_(branch_ids)))
    ).all()
    subtree_ids = [*leaf_ids, *branch_ids]
    await session.execute(
        delete(NodeTaxonomyAssignment).where(
            NodeTaxonomyAssignment.taxonomy_node_id.in_(subtree_ids)
        )
    )
    await session.execute(
        delete(TaxonomyLeafProjectionEdge).where(TaxonomyLeafProjectionEdge.leaf_id.in_(leaf_ids))
    )
    await session.execute(delete(TaxonomyNode).where(TaxonomyNode.id.in_(leaf_ids)))
    await session.execute(delete(TaxonomyNode).where(TaxonomyNode.id.in_(branch_ids)))
    await session.flush()


async def _get_root(*, session: AsyncSession) -> TaxonomyNode | None:
    return await session.scalar(select(TaxonomyNode).where(TaxonomyNode.parent_id.is_(None)))


async def _get_or_create_root(*, session: AsyncSession) -> TaxonomyNode:
    root = await _get_root(session=session)
    if root is not None:
        return root

    root = TaxonomyNode(parent_id=None, name=DEV_ROOT_NAME, depth=0, is_leaf=False)
    session.add(root)
    await session.flush()
    return root


async def _create_taxonomy_seed(
    *,
    session: AsyncSession,
    root_id: int,
) -> dict[str, int]:
    leaf_ids_by_name: dict[str, int] = {}
    for branch_name, leaf_names in DEV_SEED_BRANCHES.items():
        branch = TaxonomyNode(parent_id=root_id, name=branch_name, depth=1, is_leaf=False)
        session.add(branch)
        await session.flush()
        for leaf_name in leaf_names:
            leaf = TaxonomyNode(parent_id=branch.id, name=leaf_name, depth=2, is_leaf=True)
            session.add(leaf)
            await session.flush()
            leaf_ids_by_name[leaf_name] = leaf.id
    return leaf_ids_by_name


async def _create_card_seed(*, session: AsyncSession) -> dict[str, int]:
    repo = KnowledgeRepo(session=session)
    node_ids_by_title: dict[str, int] = {}
    placeholder_embedding = [0.0] * DEV_SEED_EMBEDDING_DIMENSIONS
    for card in DEV_SEED_CARD_SPECS:
        node_ids_by_title[card.title] = await repo.create_node(
            title=card.title,
            content=card.content,
            embedding=placeholder_embedding,
        )
    return node_ids_by_title


async def _create_assignment_seed(
    *,
    session: AsyncSession,
    leaf_ids_by_name: dict[str, int],
    node_ids_by_title: dict[str, int],
) -> None:
    for card in DEV_SEED_CARD_SPECS:
        session.add(
            NodeTaxonomyAssignment(
                node_id=node_ids_by_title[card.title],
                taxonomy_node_id=leaf_ids_by_name[card.leaf_name],
            )
        )
    await session.flush()


async def _create_edge_seed(
    *,
    session: AsyncSession,
    node_ids_by_title: dict[str, int],
) -> dict[int, tuple[int, int]]:
    edge_endpoints_by_id: dict[int, tuple[int, int]] = {}
    for edge_spec in DEV_SEED_EDGE_SPECS:
        left_id = node_ids_by_title[edge_spec.left_title]
        right_id = node_ids_by_title[edge_spec.right_title]
        node_a_id, node_b_id = sorted((left_id, right_id))
        edge = Edge(
            node_a_id=node_a_id,
            node_b_id=node_b_id,
            strength=edge_spec.strength,
        )
        session.add(edge)
        await session.flush()
        session.add_all(
            [
                Adjacency(node_id=node_a_id, edge_id=edge.id),
                Adjacency(node_id=node_b_id, edge_id=edge.id),
            ]
        )
        edge_endpoints_by_id[edge.id] = (node_a_id, node_b_id)
    await session.flush()
    return edge_endpoints_by_id


async def _create_leaf_projection_seed(
    *,
    session: AsyncSession,
    edge_endpoints_by_id: dict[int, tuple[int, int]],
    leaf_ids_by_name: dict[str, int],
    node_ids_by_title: dict[str, int],
) -> int:
    node_ids_by_leaf_id: dict[int, set[int]] = {
        leaf_id: set() for leaf_id in leaf_ids_by_name.values()
    }
    for card in DEV_SEED_CARD_SPECS:
        leaf_id = leaf_ids_by_name[card.leaf_name]
        node_ids_by_leaf_id[leaf_id].add(node_ids_by_title[card.title])

    projection_rows: list[TaxonomyLeafProjectionEdge] = []
    for leaf_id, node_ids in node_ids_by_leaf_id.items():
        for edge_id, endpoints in edge_endpoints_by_id.items():
            if endpoints[0] in node_ids or endpoints[1] in node_ids:
                projection_rows.append(TaxonomyLeafProjectionEdge(leaf_id=leaf_id, edge_id=edge_id))

    session.add_all(projection_rows)
    await session.flush()
    return len(projection_rows)


def _print_result(result: DevSeedResult) -> None:
    click.echo("mode=reset")
    click.echo(f"root_id={result.root_id}")
    click.echo(f"taxonomy_node_count={result.taxonomy_node_count}")
    click.echo(f"card_count={result.card_count}")
    click.echo(f"edge_count={result.edge_count}")
    click.echo(f"projection_edge_count={result.projection_edge_count}")


@click.command()
@click.option(
    "--reset",
    is_flag=True,
    default=False,
    help="Delete previous placeholder seed rows before inserting the fixed demo graph.",
)
def cli(*, reset: bool) -> None:
    if not reset:
        raise click.ClickException("--reset is required for the dev taxonomy-view seed.")

    try:
        result = asyncio.run(run_seed(reset=reset))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    _print_result(result)


if __name__ == "__main__":
    cli()
