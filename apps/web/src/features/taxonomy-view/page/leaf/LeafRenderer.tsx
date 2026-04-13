// abstract: Leaf-mode renderer that owns deck.gl scene state, viewport-driven hydration, and hover disclosure.
// out_of_scope: Branch React Flow rendering and page-shell chrome.

import { useEffect, useMemo, useState } from "react";

import {
  type TaxonomyLeafNodeDetailRecord,
  type TaxonomyLeafView,
  useTaxonomyLeafNodeDetailsQuery,
} from "../../data/taxonomyViewQueries";
import { buildLeafLayout } from "../layout/buildLeafLayout";
import type {
  LayoutPoint,
  LayoutViewport,
  LeafHydratedNodeLayoutInput,
} from "../layout/taxonomyLayoutTypes";
import { LeafDeckScene } from "./LeafDeckScene";
import { LeafHoverOverlay } from "./LeafHoverOverlay";
import {
  buildDefaultLeafViewport,
  LEAF_HYDRATION_OVERSCAN,
} from "./leafRendererConfig";
import type { LeafHoverState } from "./leafSceneTypes";
import { buildLeafSceneModel } from "./useLeafSceneModel";
import {
  buildLeafViewportState,
  selectLeafHydrationNodeIds,
} from "./useLeafViewportController";

interface LeafRendererProps {
  readonly center: LayoutPoint;
  readonly leafView: TaxonomyLeafView;
  readonly viewport: LayoutViewport;
}

export function LeafRenderer({
  center,
  leafView,
  viewport,
}: LeafRendererProps) {
  const [deckViewport, setDeckViewport] = useState(() =>
    buildDefaultLeafViewport(center),
  );
  const [hoverState, setHoverState] = useState<LeafHoverState | null>(null);
  const [leafDetailCache, setLeafDetailCache] = useState<
    Record<number, TaxonomyLeafNodeDetailRecord>
  >({});

  useEffect(() => {
    setDeckViewport(buildDefaultLeafViewport(center));
    setHoverState(null);
    setLeafDetailCache({});
  }, [center]);

  const leafSkeletonLayout = useMemo(
    () =>
      buildLeafLayout({
        center,
        edges: leafView.edges,
        hydratedNodeDetailsById: {},
        nodes: leafView.nodes,
        viewport,
        visibleCardNodeIds: [],
      }),
    [center, leafView.edges, leafView.nodes, viewport],
  );

  const viewportState = useMemo(
    () =>
      buildLeafViewportState({
        canvas: viewport,
        overscan: LEAF_HYDRATION_OVERSCAN,
        viewport: deckViewport,
      }),
    [deckViewport, viewport],
  );

  const visibleLeafNodeIds = useMemo(() => {
    if (!viewportState.shouldHydrateCards) {
      return [];
    }

    return selectLeafHydrationNodeIds(
      leafSkeletonLayout.nodes,
      viewportState.overscanBounds,
    );
  }, [leafSkeletonLayout.nodes, viewportState]);

  const missingLeafNodeIds = useMemo(
    () =>
      visibleLeafNodeIds.filter(
        (nodeId) => leafDetailCache[nodeId] === undefined,
      ),
    [leafDetailCache, visibleLeafNodeIds],
  );

  const leafDetailsQuery = useTaxonomyLeafNodeDetailsQuery(
    leafView.current_node.id,
    missingLeafNodeIds,
    {
      enabled:
        viewportState.shouldHydrateCards && missingLeafNodeIds.length > 0,
    },
  );

  useEffect(() => {
    if (!leafDetailsQuery.data) {
      return;
    }

    setLeafDetailCache((currentCache) => {
      const nextCache = { ...currentCache };

      for (const node of leafDetailsQuery.data.nodes) {
        nextCache[node.id] = node;
      }

      return nextCache;
    });
  }, [leafDetailsQuery.data]);

  const hydratedNodeDetailsById = useMemo<
    Partial<Record<number, LeafHydratedNodeLayoutInput>>
  >(() => {
    const scopeByNodeId = new Map(
      leafView.nodes.map((node) => [node.id, node.scope] as const),
    );
    const hydratedDetails: Partial<
      Record<number, LeafHydratedNodeLayoutInput>
    > = {};

    for (const [nodeIdKey, detail] of Object.entries(leafDetailCache)) {
      const nodeId = Number(nodeIdKey);
      const scope = scopeByNodeId.get(nodeId);

      if (!scope) {
        continue;
      }

      hydratedDetails[nodeId] = {
        ...detail,
        scope,
      };
    }

    return hydratedDetails;
  }, [leafDetailCache, leafView.nodes]);

  const leafLayout = useMemo(
    () =>
      buildLeafLayout({
        center,
        edges: leafView.edges,
        hydratedNodeDetailsById,
        nodes: leafView.nodes,
        viewport,
        visibleCardNodeIds: viewportState.shouldHydrateCards
          ? visibleLeafNodeIds
          : [],
      }),
    [
      center,
      hydratedNodeDetailsById,
      leafView.edges,
      leafView.nodes,
      viewport,
      viewportState.shouldHydrateCards,
      visibleLeafNodeIds,
    ],
  );

  const scene = useMemo(
    () =>
      buildLeafSceneModel({
        edges: leafView.edges,
        layoutNodes: leafLayout.nodes,
      }),
    [leafLayout.nodes, leafView.edges],
  );

  return (
    <div
      className="absolute inset-0"
      data-testid="taxonomy-leaf-renderer-shell"
    >
      {leafDetailsQuery.isError ? (
        <section
          className="absolute right-6 bottom-6 z-20 w-[min(360px,calc(100%-48px))] rounded-[18px] border border-[rgba(148,163,184,0.24)] bg-[rgba(255,255,255,0.94)] p-4 text-left shadow-[0_18px_40px_rgba(15,23,42,0.12)]"
          data-testid="taxonomy-leaf-hydration-error"
          role="alert"
        >
          <h2 className="m-0 text-[0.95rem] text-[#0F172A]">
            Leaf details unavailable
          </h2>
          <p className="mt-2 mb-0 text-sm text-[#475569]">
            {leafDetailsQuery.error.message}
          </p>
        </section>
      ) : null}
      <LeafDeckScene
        hoveredNodeId={hoverState?.card.graphNodeId ?? null}
        onHoverChange={setHoverState}
        onViewportChange={setDeckViewport}
        scene={scene}
        viewport={deckViewport}
      />
      <LeafHoverOverlay hoverState={hoverState} />
    </div>
  );
}
