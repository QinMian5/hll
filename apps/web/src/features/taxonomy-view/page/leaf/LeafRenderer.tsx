// abstract: Leaf-mode renderer that owns deck.gl scene state, title hydration, and disclosure state.
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
  type TaxonomyLeafLayoutBounds,
  type TaxonomyLeafLayoutSliceResponse,
  type TaxonomyLeafNodeDetailRecord,
  type TaxonomyLeafView,
  useTaxonomyLeafLayoutSliceQuery,
  useTaxonomyLeafNodeDetailsQuery,
  useTaxonomyLeafNodeTitlesQuery,
} from "../../data/taxonomyViewQueries";
import type {
  LayoutViewport,
  TaxonomyLayoutNode,
} from "../layout/taxonomyLayoutTypes";
import {
  buildDefaultLeafViewport,
  LEAF_HYDRATION_OVERSCAN,
  LEAF_LAYOUT_TILE_SIZE,
} from "./leafRendererConfig";
import type {
  LeafDisclosureState,
  LeafScenePointNode,
  LeafWorldBounds,
} from "./leafSceneTypes";
import {
  buildLeafSceneModelBase,
  buildLeafTitleLabelNodes,
} from "./useLeafSceneModel";
import {
  buildLeafViewportState,
  isLeafPointTitleModeActive,
  selectLeafHydrationNodeIds,
  snapLeafWorldBoundsToTile,
} from "./useLeafViewportController";

interface LeafRendererProps {
  readonly leafView: TaxonomyLeafView;
  readonly onSuggestEdit?: (card: SearchResultCardEditPayload) => void;
  readonly viewport: LayoutViewport;
}

const LeafDeckScene = lazy(() =>
  import("./LeafDeckScene").then((module) => ({
    default: module.LeafDeckScene,
  })),
);

const LEAF_POINT_DIAMETER = 8;

interface RenderableLeafLayout {
  readonly edges: TaxonomyLeafLayoutSliceResponse["edges"];
  readonly nodes: TaxonomyLayoutNode[];
}

function toLayoutBounds(bounds: LeafWorldBounds): TaxonomyLeafLayoutBounds {
  return {
    max_x: bounds.right,
    max_y: bounds.bottom,
    min_x: bounds.left,
    min_y: bounds.top,
  };
}

function buildRenderableLeafLayout(
  layoutSlice: TaxonomyLeafLayoutSliceResponse | undefined,
): RenderableLeafLayout {
  if (!layoutSlice) {
    return { edges: [], nodes: [] };
  }

  return {
    edges: layoutSlice.edges,
    nodes: layoutSlice.nodes.map((node) => ({
      data: {
        depth: 0,
        graphNodeId: node.id,
        label: "",
        renderMode: "point" as const,
        scope: node.scope,
        targetNodeId: null,
        tooltip: "",
      },
      id: `leaf-${node.id}`,
      position: {
        x: node.x - LEAF_POINT_DIAMETER / 2,
        y: node.y - LEAF_POINT_DIAMETER / 2,
      },
      style: {
        borderRadius: `${LEAF_POINT_DIAMETER}px`,
        height: LEAF_POINT_DIAMETER,
        width: LEAF_POINT_DIAMETER,
      },
      type: "bubble" as const,
    })),
  };
}

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
  leafView,
  onSuggestEdit,
  viewport,
}: LeafRendererProps) {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const lastLeafLayoutSliceRef = useRef<
    TaxonomyLeafLayoutSliceResponse | undefined
  >(undefined);
  const {
    max_x: leafWorldMaxX,
    max_y: leafWorldMaxY,
    min_x: leafWorldMinX,
    min_y: leafWorldMinY,
  } = leafView.world_bounds;
  const initialLeafViewportCenter = useMemo(
    () => ({
      x: (leafWorldMinX + leafWorldMaxX) / 2,
      y: (leafWorldMinY + leafWorldMaxY) / 2,
    }),
    [leafWorldMaxX, leafWorldMaxY, leafWorldMinX, leafWorldMinY],
  );
  const initialDeckViewport = useMemo(
    () => buildDefaultLeafViewport(initialLeafViewportCenter),
    [initialLeafViewportCenter],
  );
  const [canvasViewport, setCanvasViewport] = useState(viewport);
  const [deckViewportSnapshot, setDeckViewportSnapshot] =
    useState(initialDeckViewport);
  const deferredDeckViewportSnapshot = useDeferredValue(deckViewportSnapshot);
  const liveViewportRef = useRef(initialDeckViewport);
  const [isPointTitleModeActive, setIsPointTitleModeActive] = useState(() =>
    isLeafPointTitleModeActive(initialDeckViewport.zoom),
  );
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
    setIsPointTitleModeActive(
      isLeafPointTitleModeActive(initialDeckViewport.zoom),
    );
    setHoveredPointNodeId(null);
    setSelectedNodeId(null);
    setLeafTitleCache({});
    setLeafDetailCache({});
    lastLeafLayoutSliceRef.current = undefined;
  }, [initialDeckViewport, leafNodeId]);

  const handleViewportFrameChange = useCallback(
    (viewport: typeof initialDeckViewport) => {
      liveViewportRef.current = viewport;
      setIsPointTitleModeActive((currentValue) => {
        const nextValue = isLeafPointTitleModeActive(viewport.zoom);
        return currentValue === nextValue ? currentValue : nextValue;
      });
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

  const viewportState = useMemo(
    () =>
      buildLeafViewportState({
        canvas: canvasViewport,
        overscan: LEAF_HYDRATION_OVERSCAN,
        viewport: deferredDeckViewportSnapshot,
      }),
    [canvasViewport, deferredDeckViewportSnapshot],
  );
  const leafLayoutBounds = useMemo(
    () =>
      toLayoutBounds(
        snapLeafWorldBoundsToTile(
          viewportState.overscanBounds,
          LEAF_LAYOUT_TILE_SIZE,
        ),
      ),
    [viewportState.overscanBounds],
  );
  const leafLayoutQuery = useTaxonomyLeafLayoutSliceQuery(
    leafNodeId,
    leafLayoutBounds,
    { enabled: Number.isFinite(leafNodeId) },
  );
  useEffect(() => {
    if (leafLayoutQuery.data) {
      lastLeafLayoutSliceRef.current = leafLayoutQuery.data;
    }
  }, [leafLayoutQuery.data]);
  const renderLeafLayoutSlice =
    leafLayoutQuery.data ?? lastLeafLayoutSliceRef.current;
  const leafLayout = useMemo(
    () => buildRenderableLeafLayout(renderLeafLayoutSlice),
    [renderLeafLayoutSlice],
  );

  useEffect(() => {
    if (isPointTitleModeActive) {
      return;
    }

    setHoveredPointNodeId(null);
    setSelectedNodeId(null);
  }, [isPointTitleModeActive]);

  const visibleTitleNodeIds = useMemo(() => {
    if (!isPointTitleModeActive) {
      return [];
    }

    return selectLeafHydrationNodeIds(
      leafLayout.nodes,
      viewportState.overscanBounds,
    );
  }, [isPointTitleModeActive, leafLayout.nodes, viewportState.overscanBounds]);

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
      enabled: isPointTitleModeActive && missingTitleNodeIds.length > 0,
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
    if (!isPointTitleModeActive) {
      return [];
    }

    if (selectedNodeId !== null) {
      return [selectedNodeId];
    }

    return hoveredPointNodeId === null ? [] : [hoveredPointNodeId];
  }, [hoveredPointNodeId, isPointTitleModeActive, selectedNodeId]);
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
      enabled: isPointTitleModeActive && missingDetailNodeIds.length > 0,
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
        edges: leafLayout.edges,
        layoutNodes: leafLayout.nodes,
      }),
    [leafLayout.edges, leafLayout.nodes],
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
  const activeFocusNodeId = isPointTitleModeActive
    ? (selectedNodeId ?? hoveredPointNodeId)
    : null;
  const disclosure = useMemo<LeafDisclosureState | null>(() => {
    if (!isPointTitleModeActive) {
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
    isPointTitleModeActive,
    leafDetailCache,
    pointNodesById,
    selectedNodeId,
  ]);
  const hiddenLabelNodeId = disclosure?.node.graphNodeId ?? null;
  const hydrationError = leafLayoutQuery.isError
    ? leafLayoutQuery.error
    : leafTitlesQuery.isError
      ? leafTitlesQuery.error
      : leafDetailsQuery.isError
        ? leafDetailsQuery.error
        : null;

  const handlePointHover = useCallback(
    (nodeId: number | null) => {
      if (!isPointTitleModeActive) {
        setHoveredPointNodeId(null);
        return;
      }

      setHoveredPointNodeId(nodeId);
    },
    [isPointTitleModeActive],
  );
  const handlePointClick = useCallback(
    (nodeId: number) => {
      if (!isPointTitleModeActive) {
        return;
      }

      setSelectedNodeId((currentNodeId) =>
        currentNodeId === nodeId ? null : nodeId,
      );
    },
    [isPointTitleModeActive],
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
          disclosure={disclosure}
          hiddenLabelNodeId={hiddenLabelNodeId}
          hoveredPointNodeId={hoveredPointNodeId}
          initialViewport={initialDeckViewport}
          isPointInteractionEnabled={isPointTitleModeActive}
          onCanvasClick={handleCanvasClick}
          onPointClick={handlePointClick}
          onPointHover={handlePointHover}
          onSuggestEdit={onSuggestEdit}
          onViewportFrameChange={handleViewportFrameChange}
          onViewportChange={setDeckViewportSnapshot}
          scene={scene}
        />
      </Suspense>
    </div>
  );
}
