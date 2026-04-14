// abstract: Leaf-mode renderer that owns deck.gl scene state, viewport-driven hydration, and hover disclosure.
// out_of_scope: Branch React Flow rendering and page-shell chrome.

import {
  startTransition,
  useCallback,
  useDeferredValue,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

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
  LeafRichTextCardsOverlay,
  type LeafRichTextCardsOverlayHandle,
} from "./LeafRichTextCardsOverlay";
import {
  buildDefaultLeafViewport,
  LEAF_HYDRATION_OVERSCAN,
} from "./leafRendererConfig";
import type { LeafHoverState } from "./leafSceneTypes";
import {
  buildLeafCardNodes,
  buildLeafSceneModelBase,
  filterLeafPointNodes,
} from "./useLeafSceneModel";
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
  const shellRef = useRef<HTMLDivElement | null>(null);
  const initialDeckViewport = useMemo(
    () => buildDefaultLeafViewport(center),
    [center],
  );
  const overlayRef = useRef<LeafRichTextCardsOverlayHandle | null>(null);
  const [canvasViewport, setCanvasViewport] = useState(viewport);
  const [deckViewportSnapshot, setDeckViewportSnapshot] =
    useState(initialDeckViewport);
  const deferredDeckViewportSnapshot = useDeferredValue(deckViewportSnapshot);
  const liveViewportRef = useRef(initialDeckViewport);
  const [hoverState, setHoverState] = useState<LeafHoverState | null>(null);
  const [leafDetailCache, setLeafDetailCache] = useState<
    Record<number, TaxonomyLeafNodeDetailRecord>
  >({});
  const [measuredCardSizesById, setMeasuredCardSizesById] = useState<
    Record<number, { readonly height: number; readonly width: number }>
  >({});

  useEffect(() => {
    liveViewportRef.current = initialDeckViewport;
    setDeckViewportSnapshot(initialDeckViewport);
    setHoverState(null);
    setLeafDetailCache({});
    setMeasuredCardSizesById({});
  }, [initialDeckViewport]);

  const handleViewportFrameChange = useCallback(
    (viewport: typeof initialDeckViewport) => {
      liveViewportRef.current = viewport;
      overlayRef.current?.syncViewport(viewport);
    },
    [],
  );

  useLayoutEffect(() => {
    const element = shellRef.current;

    if (!element) {
      return;
    }

    function updateCanvasViewport(width: number, height: number) {
      if (width <= 0 || height <= 0) {
        return;
      }

      setCanvasViewport((currentViewport) => {
        if (
          currentViewport.width === width &&
          currentViewport.height === height
        ) {
          return currentViewport;
        }

        return { height, width };
      });
    }

    const rect = element.getBoundingClientRect();
    updateCanvasViewport(rect.width, rect.height);

    if (typeof ResizeObserver === "undefined") {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];

      if (!entry) {
        return;
      }

      updateCanvasViewport(entry.contentRect.width, entry.contentRect.height);
    });

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, []);

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
  const lockedNodeCentersById = useMemo(
    () =>
      new Map(
        leafSkeletonLayout.nodes
          .map((node) => {
            const graphNodeId = node.data.graphNodeId;

            if (!Number.isFinite(graphNodeId)) {
              return null;
            }

            return [
              graphNodeId,
              {
                x: node.position.x + node.style.width / 2,
                y: node.position.y + node.style.height / 2,
              },
            ] as const;
          })
          .filter(
            (
              entry,
            ): entry is readonly [
              number,
              {
                readonly x: number;
                readonly y: number;
              },
            ] => entry !== null,
          ),
      ),
    [leafSkeletonLayout.nodes],
  );

  const viewportState = useMemo(
    () =>
      buildLeafViewportState({
        canvas: canvasViewport,
        overscan: LEAF_HYDRATION_OVERSCAN,
        viewport: deferredDeckViewportSnapshot,
      }),
    [canvasViewport, deferredDeckViewportSnapshot],
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

    startTransition(() => {
      setLeafDetailCache((currentCache) => {
        let hasChanges = false;
        const nextCache = { ...currentCache };

        for (const node of leafDetailsQuery.data.nodes) {
          if (nextCache[node.id] === node) {
            continue;
          }

          nextCache[node.id] = node;
          hasChanges = true;
        }

        return hasChanges ? nextCache : currentCache;
      });
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
        lockedNodeCentersById,
        measuredCardSizesById,
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
      lockedNodeCentersById,
      measuredCardSizesById,
      viewport,
      viewportState.shouldHydrateCards,
      visibleLeafNodeIds,
    ],
  );

  const leafSceneBase = useMemo(
    () =>
      buildLeafSceneModelBase({
        edges: leafView.edges,
        layoutNodes: leafSkeletonLayout.nodes,
      }),
    [leafSkeletonLayout.nodes, leafView.edges],
  );
  const scene = useMemo(() => {
    const cardNodes = buildLeafCardNodes(leafLayout.nodes);

    return {
      ...leafSceneBase,
      cardNodes,
      pointNodes: filterLeafPointNodes({
        cardNodes,
        pointNodes: leafSceneBase.pointNodes,
      }),
    };
  }, [leafLayout.nodes, leafSceneBase]);
  const handleCardMeasurementsChange = useCallback(
    (
      measurements: ReadonlyArray<{
        readonly graphNodeId: number;
        readonly height: number;
        readonly width: number;
      }>,
    ) => {
      startTransition(() => {
        setMeasuredCardSizesById((currentSizes) => {
          let hasChanges = false;
          const nextSizes = { ...currentSizes };

          for (const measurement of measurements) {
            const currentMeasurement = currentSizes[measurement.graphNodeId];

            if (
              currentMeasurement &&
              currentMeasurement.width === measurement.width &&
              currentMeasurement.height === measurement.height
            ) {
              continue;
            }

            nextSizes[measurement.graphNodeId] = {
              height: measurement.height,
              width: measurement.width,
            };
            hasChanges = true;
          }

          return hasChanges ? nextSizes : currentSizes;
        });
      });
    },
    [],
  );

  return (
    <div
      className="absolute inset-0"
      data-testid="taxonomy-leaf-renderer-shell"
      ref={shellRef}
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
        initialViewport={initialDeckViewport}
        onViewportFrameChange={handleViewportFrameChange}
        onViewportChange={setDeckViewportSnapshot}
        scene={scene}
      />
      <LeafRichTextCardsOverlay
        canvas={canvasViewport}
        cardNodes={scene.cardNodes}
        hoveredNodeId={hoverState?.card.graphNodeId ?? null}
        neighborNodeIdsByNodeId={scene.neighborNodeIdsByNodeId}
        onCardMeasurementsChange={handleCardMeasurementsChange}
        onHoverChange={setHoverState}
        ref={overlayRef}
        viewport={liveViewportRef.current}
      />
      <LeafHoverOverlay hoverState={hoverState} />
    </div>
  );
}
