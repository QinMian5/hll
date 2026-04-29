// abstract: Leaf-mode renderer that owns deck.gl scene state, title labels, and disclosure hydration.
// out_of_scope: Branch React Flow rendering and page-shell chrome.

import {
  lazy,
  Suspense,
  startTransition,
  useCallback,
  useDeferredValue,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { SearchResultCardEditPayload } from "../../../search/components/SearchResultCard";
import {
  type TaxonomyLeafNodeDetailRecord,
  type TaxonomyLeafView,
  useTaxonomyLeafNodeDetailsQuery,
  useTaxonomyLeafNodeTitlesQuery,
} from "../../data/taxonomyViewQueries";
import { buildLeafLayout } from "../layout/buildLeafLayout";
import type {
  LayoutPoint,
  LayoutViewport,
} from "../layout/taxonomyLayoutTypes";
import {
  LeafDisclosureOverlay,
  type LeafDisclosureOverlayHandle,
} from "./LeafDisclosureOverlay";
import {
  LeafTitleLabelsOverlay,
  type LeafTitleLabelsOverlayHandle,
} from "./LeafTitleLabelsOverlay";
import {
  buildDefaultLeafViewport,
  LEAF_HYDRATION_OVERSCAN,
} from "./leafRendererConfig";
import type { LeafDisclosureState, LeafScenePointNode } from "./leafSceneTypes";
import {
  buildLeafSceneModelBase,
  buildLeafTitleLabelNodes,
} from "./useLeafSceneModel";
import {
  buildLeafViewportState,
  selectLeafHydrationNodeIds,
} from "./useLeafViewportController";

interface LeafRendererProps {
  readonly center: LayoutPoint;
  readonly leafView: TaxonomyLeafView;
  readonly onSuggestEdit?: (card: SearchResultCardEditPayload) => void;
  readonly viewport: LayoutViewport;
}

const LeafDeckScene = lazy(() =>
  import("./LeafDeckScene").then((module) => ({
    default: module.LeafDeckScene,
  })),
);

function buildDisclosureNode(options: {
  readonly detail: TaxonomyLeafNodeDetailRecord | undefined;
  readonly pointNode: LeafScenePointNode | undefined;
}) {
  if (!options.detail || !options.pointNode) {
    return null;
  }

  return {
    content: options.detail.content,
    currentVersion: options.detail.current_version,
    graphNodeId: options.pointNode.graphNodeId,
    id: options.pointNode.id,
    position: options.pointNode.position,
    scope: options.pointNode.scope,
    title: options.detail.title,
  };
}

export function LeafRenderer({
  center,
  leafView,
  onSuggestEdit,
  viewport,
}: LeafRendererProps) {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const titleLabelsRef = useRef<LeafTitleLabelsOverlayHandle | null>(null);
  const disclosureRef = useRef<LeafDisclosureOverlayHandle | null>(null);
  const initialDeckViewport = useMemo(
    () => buildDefaultLeafViewport(center),
    [center],
  );
  const [canvasViewport, setCanvasViewport] = useState(viewport);
  const [deckViewportSnapshot, setDeckViewportSnapshot] =
    useState(initialDeckViewport);
  const deferredDeckViewportSnapshot = useDeferredValue(deckViewportSnapshot);
  const liveViewportRef = useRef(initialDeckViewport);
  const [hoveredPointNodeId, setHoveredPointNodeId] = useState<number | null>(
    null,
  );
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [leafTitleCache, setLeafTitleCache] = useState<Record<number, string>>(
    {},
  );
  const [leafDetailCache, setLeafDetailCache] = useState<
    Record<number, TaxonomyLeafNodeDetailRecord>
  >({});
  const leafNodeId = leafView.current_node.id;

  useEffect(() => {
    if (!Number.isFinite(leafNodeId)) {
      return;
    }

    liveViewportRef.current = initialDeckViewport;
    setDeckViewportSnapshot(initialDeckViewport);
    setHoveredPointNodeId(null);
    setSelectedNodeId(null);
    setLeafTitleCache({});
    setLeafDetailCache({});
  }, [initialDeckViewport, leafNodeId]);

  const handleViewportFrameChange = useCallback(
    (viewport: typeof initialDeckViewport) => {
      liveViewportRef.current = viewport;
      titleLabelsRef.current?.syncViewport(viewport);
      disclosureRef.current?.syncViewport(viewport);
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

  const leafLayout = useMemo(
    () =>
      buildLeafLayout({
        center,
        edges: leafView.edges,
        nodes: leafView.nodes,
        viewport,
      }),
    [center, leafView.edges, leafView.nodes, viewport],
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

  useEffect(() => {
    if (viewportState.isPointTitleModeActive) {
      return;
    }

    setHoveredPointNodeId(null);
    setSelectedNodeId(null);
  }, [viewportState.isPointTitleModeActive]);

  const visibleTitleNodeIds = useMemo(() => {
    if (!viewportState.isPointTitleModeActive) {
      return [];
    }

    return selectLeafHydrationNodeIds(
      leafLayout.nodes,
      viewportState.overscanBounds,
    );
  }, [leafLayout.nodes, viewportState]);

  const missingTitleNodeIds = useMemo(
    () =>
      visibleTitleNodeIds.filter(
        (nodeId) => leafTitleCache[nodeId] === undefined,
      ),
    [leafTitleCache, visibleTitleNodeIds],
  );

  const leafTitlesQuery = useTaxonomyLeafNodeTitlesQuery(
    leafNodeId,
    missingTitleNodeIds,
    {
      enabled:
        viewportState.isPointTitleModeActive && missingTitleNodeIds.length > 0,
    },
  );

  useEffect(() => {
    if (!leafTitlesQuery.data) {
      return;
    }

    startTransition(() => {
      setLeafTitleCache((currentCache) => {
        let hasChanges = false;
        const nextCache = { ...currentCache };

        for (const node of leafTitlesQuery.data.nodes) {
          if (nextCache[node.id] === node.title) {
            continue;
          }

          nextCache[node.id] = node.title;
          hasChanges = true;
        }

        return hasChanges ? nextCache : currentCache;
      });
    });
  }, [leafTitlesQuery.data]);

  const detailTargetNodeIds = useMemo(() => {
    if (!viewportState.isPointTitleModeActive) {
      return [];
    }

    if (selectedNodeId !== null) {
      return [selectedNodeId];
    }

    return hoveredPointNodeId === null ? [] : [hoveredPointNodeId];
  }, [
    hoveredPointNodeId,
    selectedNodeId,
    viewportState.isPointTitleModeActive,
  ]);
  const missingDetailNodeIds = useMemo(
    () =>
      detailTargetNodeIds.filter(
        (nodeId) => leafDetailCache[nodeId] === undefined,
      ),
    [detailTargetNodeIds, leafDetailCache],
  );

  const leafDetailsQuery = useTaxonomyLeafNodeDetailsQuery(
    leafNodeId,
    missingDetailNodeIds,
    {
      enabled:
        viewportState.isPointTitleModeActive && missingDetailNodeIds.length > 0,
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
      setLeafTitleCache((currentCache) => {
        let hasChanges = false;
        const nextCache = { ...currentCache };

        for (const node of leafDetailsQuery.data.nodes) {
          if (nextCache[node.id] === node.title) {
            continue;
          }

          nextCache[node.id] = node.title;
          hasChanges = true;
        }

        return hasChanges ? nextCache : currentCache;
      });
    });
  }, [leafDetailsQuery.data]);

  const leafSceneBase = useMemo(
    () =>
      buildLeafSceneModelBase({
        edges: leafView.edges,
        layoutNodes: leafLayout.nodes,
      }),
    [leafLayout.nodes, leafView.edges],
  );
  const titleLabelNodes = useMemo(
    () =>
      buildLeafTitleLabelNodes({
        pointNodes: leafSceneBase.pointNodes,
        titlesByNodeId: leafTitleCache,
        visibleNodeIds: visibleTitleNodeIds,
      }),
    [leafSceneBase.pointNodes, leafTitleCache, visibleTitleNodeIds],
  );
  const scene = useMemo(
    () => ({
      ...leafSceneBase,
      titleLabelNodes,
    }),
    [leafSceneBase, titleLabelNodes],
  );
  const pointNodesById = useMemo(
    () =>
      new Map(
        scene.pointNodes.map(
          (pointNode) => [pointNode.graphNodeId, pointNode] as const,
        ),
      ),
    [scene.pointNodes],
  );
  const activeFocusNodeId = viewportState.isPointTitleModeActive
    ? (selectedNodeId ?? hoveredPointNodeId)
    : null;
  const disclosure = useMemo<LeafDisclosureState | null>(() => {
    if (!viewportState.isPointTitleModeActive) {
      return null;
    }

    if (selectedNodeId !== null) {
      const node = buildDisclosureNode({
        detail: leafDetailCache[selectedNodeId],
        pointNode: pointNodesById.get(selectedNodeId),
      });

      return node ? { mode: "selected", node } : null;
    }

    if (hoveredPointNodeId !== null) {
      const node = buildDisclosureNode({
        detail: leafDetailCache[hoveredPointNodeId],
        pointNode: pointNodesById.get(hoveredPointNodeId),
      });

      return node ? { mode: "hover", node } : null;
    }

    return null;
  }, [
    hoveredPointNodeId,
    leafDetailCache,
    pointNodesById,
    selectedNodeId,
    viewportState.isPointTitleModeActive,
  ]);
  const hiddenLabelNodeId = disclosure?.node.graphNodeId ?? null;
  const hydrationError = leafTitlesQuery.isError
    ? leafTitlesQuery.error
    : leafDetailsQuery.isError
      ? leafDetailsQuery.error
      : null;

  const handlePointHover = useCallback(
    (nodeId: number | null) => {
      if (!viewportState.isPointTitleModeActive) {
        setHoveredPointNodeId(null);
        return;
      }

      setHoveredPointNodeId(nodeId);
    },
    [viewportState.isPointTitleModeActive],
  );
  const handlePointClick = useCallback(
    (nodeId: number) => {
      if (!viewportState.isPointTitleModeActive) {
        return;
      }

      setSelectedNodeId((currentNodeId) =>
        currentNodeId === nodeId ? null : nodeId,
      );
    },
    [viewportState.isPointTitleModeActive],
  );
  const handleCanvasClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  return (
    <div
      className="absolute inset-0"
      data-testid="taxonomy-leaf-renderer-shell"
      ref={shellRef}
    >
      {hydrationError ? (
        <section
          className="absolute right-6 bottom-6 z-20 w-[min(360px,calc(100%-48px))] rounded-[10px] border border-[rgba(148,163,184,0.24)] bg-[rgba(255,255,255,0.94)] p-4 text-left shadow-[0_18px_40px_rgba(15,23,42,0.12)]"
          data-testid="taxonomy-leaf-hydration-error"
          role="alert"
        >
          <h2 className="m-0 text-[0.95rem] text-[#0F172A]">
            Leaf details unavailable
          </h2>
          <p className="mt-2 mb-0 text-sm text-[#475569]">
            {hydrationError.message}
          </p>
        </section>
      ) : null}
      <Suspense fallback={null}>
        <LeafDeckScene
          activeFocusNodeId={activeFocusNodeId}
          hoveredPointNodeId={hoveredPointNodeId}
          initialViewport={initialDeckViewport}
          isPointInteractionEnabled={viewportState.isPointTitleModeActive}
          onCanvasClick={handleCanvasClick}
          onPointClick={handlePointClick}
          onPointHover={handlePointHover}
          onViewportFrameChange={handleViewportFrameChange}
          onViewportChange={setDeckViewportSnapshot}
          scene={scene}
        />
      </Suspense>
      <LeafTitleLabelsOverlay
        canvas={canvasViewport}
        hiddenLabelNodeId={hiddenLabelNodeId}
        ref={titleLabelsRef}
        titleLabelNodes={scene.titleLabelNodes}
        viewport={liveViewportRef.current}
      />
      <LeafDisclosureOverlay
        canvas={canvasViewport}
        disclosure={disclosure}
        onSuggestEdit={onSuggestEdit}
        ref={disclosureRef}
        viewport={liveViewportRef.current}
      />
    </div>
  );
}
