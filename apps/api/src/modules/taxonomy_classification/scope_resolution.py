"""
Abstract: Name and path based scope resolution for taxonomy-classification submissions.
Out of scope: Job creation and remote queue transport.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.taxonomy.model import TaxonomyNode
from modules.taxonomy_classification.dto import TaxonomyClassificationSubmissionSelection


class TaxonomyClassificationScopeResolutionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ResolvedTaxonomyClassificationScope:
    scope_node: TaxonomyNode
    regular_children: tuple[TaxonomyNode, ...]
    breadcrumb: tuple[str, ...]

    @property
    def has_regular_children(self) -> bool:
        return bool(self.regular_children)


async def resolve_taxonomy_classification_scopes(
    session: AsyncSession,
    selection: TaxonomyClassificationSubmissionSelection,
) -> list[ResolvedTaxonomyClassificationScope]:
    nodes = list(
        await session.scalars(
            select(TaxonomyNode).order_by(
                TaxonomyNode.depth.asc(),
                TaxonomyNode.name.asc(),
                TaxonomyNode.id.asc(),
            )
        )
    )
    index = _TaxonomyScopeIndex(nodes)
    if selection.kind == "scope_name":
        if selection.scope_name is None:
            raise TaxonomyClassificationScopeResolutionError("scope_name is required.")
        return [index.resolve_scope_name(selection.scope_name)]
    if selection.kind == "scope_path":
        if selection.scope_path is None:
            raise TaxonomyClassificationScopeResolutionError("scope_path is required.")
        return [index.resolve_scope_path(selection.scope_path)]
    return index.resolve_all_direct_assignments()


class _TaxonomyScopeIndex:
    def __init__(self, nodes: list[TaxonomyNode]) -> None:
        self._node_by_id = {node.id: node for node in nodes}
        self._children_by_parent_id: dict[int | None, list[TaxonomyNode]] = defaultdict(list)
        for node in nodes:
            self._children_by_parent_id[node.parent_id].append(node)

    def resolve_scope_name(self, scope_name: str) -> ResolvedTaxonomyClassificationScope:
        normalized_name = _normalize_name(scope_name)
        candidates = [
            node
            for node in self._node_by_id.values()
            if _normalize_name(node.name) == normalized_name
        ]
        if not candidates:
            raise TaxonomyClassificationScopeResolutionError(
                f"No regular taxonomy node matches scope name '{scope_name}'."
            )
        if len(candidates) > 1:
            candidate_list = self._format_candidates(candidates)
            raise TaxonomyClassificationScopeResolutionError(
                "Multiple taxonomy nodes match scope name "
                f"'{scope_name}'. Use a more precise scope path. Candidates: {candidate_list}."
            )
        return self._build_resolved_scope(candidates[0])

    def resolve_scope_path(
        self,
        scope_path: tuple[str, ...],
    ) -> ResolvedTaxonomyClassificationScope:
        candidates = self._children_by_name(parent_id=None, name=scope_path[0])
        if not candidates:
            raise TaxonomyClassificationScopeResolutionError(
                f"Missing taxonomy path segment '{scope_path[0]}' below <root>."
            )
        if len(candidates) > 1:
            raise TaxonomyClassificationScopeResolutionError(
                "Ambiguous taxonomy path segment "
                f"'{scope_path[0]}' below <root>. Candidates: "
                f"{self._format_candidates(candidates)}."
            )

        current = candidates[0]
        for segment in scope_path[1:]:
            children = self._children_by_name(parent_id=current.id, name=segment)
            current_breadcrumb = _format_breadcrumb(self._breadcrumb(current))
            if not children:
                raise TaxonomyClassificationScopeResolutionError(
                    f"Missing taxonomy path segment '{segment}' below {current_breadcrumb}."
                )
            if len(children) > 1:
                raise TaxonomyClassificationScopeResolutionError(
                    "Ambiguous taxonomy path segment "
                    f"'{segment}' below {current_breadcrumb}. Candidates: "
                    f"{self._format_candidates(children)}."
                )
            current = children[0]

        return self._build_resolved_scope(current)

    def resolve_all_direct_assignments(self) -> list[ResolvedTaxonomyClassificationScope]:
        scopes = [self._build_resolved_scope(node) for node in self._node_by_id.values()]
        return sorted(scopes, key=lambda scope: (scope.breadcrumb, scope.scope_node.id))

    def _build_resolved_scope(
        self,
        scope_node: TaxonomyNode,
    ) -> ResolvedTaxonomyClassificationScope:
        regular_children = tuple(
            child
            for child in self._children_by_parent_id.get(scope_node.id, [])
            if child.name != "Unclassified"
        )
        return ResolvedTaxonomyClassificationScope(
            scope_node=scope_node,
            regular_children=regular_children,
            breadcrumb=self._breadcrumb(scope_node),
        )

    def _children_by_name(self, *, parent_id: int | None, name: str) -> list[TaxonomyNode]:
        normalized_name = _normalize_name(name)
        return [
            child
            for child in self._children_by_parent_id.get(parent_id, [])
            if _normalize_name(child.name) == normalized_name
        ]

    def _breadcrumb(self, node: TaxonomyNode) -> tuple[str, ...]:
        names: list[str] = [node.name]
        current = node
        while current.parent_id is not None:
            parent = self._node_by_id[current.parent_id]
            names.append(parent.name)
            current = parent
        return tuple(reversed(names))

    def _format_candidates(self, candidates: list[TaxonomyNode]) -> str:
        sorted_candidates = sorted(candidates, key=lambda node: (self._breadcrumb(node), node.id))
        return "; ".join(
            f"{_format_breadcrumb(self._breadcrumb(node))} (id={node.id})"
            for node in sorted_candidates
        )


def _normalize_name(name: str) -> str:
    return name.casefold()


def _format_breadcrumb(breadcrumb: tuple[str, ...]) -> str:
    return " / ".join(breadcrumb)


__all__ = [
    "ResolvedTaxonomyClassificationScope",
    "TaxonomyClassificationScopeResolutionError",
    "resolve_taxonomy_classification_scopes",
]
