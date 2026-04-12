// abstract: Taxonomy-query-driven React Flow page with dedicated branch and leaf layouts.
// out_of_scope: Backend taxonomy read orchestration and page-shell redesign.

import "@xyflow/react/dist/style.css";

import { Background, type Edge, type Node, ReactFlow } from "@xyflow/react";
import { startTransition, useEffect, useMemo, useState } from "react";
import {
  type TaxonomyLeafNodeDetailRecord,
  useTaxonomyLeafNodeDetailsQuery,
  useTaxonomyNodeViewQuery,
  useTaxonomyRootViewQuery,
} from "../data/taxonomyViewQueries";
import { buildBranchLayout } from "./layout/buildBranchLayout";
import { buildLeafLayout } from "./layout/buildLeafLayout";
import type {
  LeafHydratedNodeLayoutInput,
  TaxonomyLayoutNodeData,
} from "./layout/taxonomyLayoutTypes";
import { TaxonomyFlowNode } from "./TaxonomyFlowNode";

const BRANCH_LAYOUT_VIEWPORT = { height: 900, width: 1404 };
const LAYOUT_CENTER = { x: 702, y: 450 };
const breadcrumbMutedClasses =
  "text-[13px] leading-[18px] font-normal text-[rgba(92,107,138,0.74)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0";
const breadcrumbCurrentClasses =
  "text-[13px] leading-[18px] font-medium text-[rgba(33,43,64,0.96)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0";
const DEFAULT_FLOW_VIEWPORT = { x: 0, y: 0, zoom: 0.45 };
export const LEAF_CARD_ACTIVATION_ZOOM = 0.85;
export const LEAF_HYDRATION_OVERSCAN = 160;

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;
interface FlowViewport {
  readonly x: number;
  readonly y: number;
  readonly zoom: number;
}

interface FlowBounds {
  readonly bottom: number;
  readonly left: number;
  readonly right: number;
  readonly top: number;
}

const nodeTypes = {
  bubble: TaxonomyFlowNode,
};

function toFlowNode(
  node: ReturnType<typeof buildBranchLayout>["nodes"][number],
): BubbleFlowNode {
  return {
    data: node.data,
    draggable: false,
    id: node.id,
    position: node.position,
    selectable: false,
    style: node.style,
    type: node.type,
  };
}

function toFlowEdge(
  edge: ReturnType<typeof buildLeafLayout>["edges"][number],
): Edge {
  return {
    focusable: false,
    id: edge.id,
    selectable: false,
    source: edge.source,
    style: {
      pointerEvents: "none",
    },
    target: edge.target,
    type: "straight",
  };
}

export function flowBoundsFromViewport(
  viewport: FlowViewport,
  canvas: { readonly height: number; readonly width: number },
  overscan = 0,
): FlowBounds {
  return {
    bottom: (canvas.height - viewport.y) / viewport.zoom + overscan,
    left: -viewport.x / viewport.zoom - overscan,
    right: (canvas.width - viewport.x) / viewport.zoom + overscan,
    top: -viewport.y / viewport.zoom - overscan,
  };
}

export function selectLeafHydrationNodeIds(
  nodes: ReadonlyArray<ReturnType<typeof buildLeafLayout>["nodes"][number]>,
  viewport: FlowViewport,
  canvas: { readonly height: number; readonly width: number },
  overscan = LEAF_HYDRATION_OVERSCAN,
): number[] {
  const bounds = flowBoundsFromViewport(viewport, canvas, overscan);

  return nodes
    .filter((node) => {
      const left = node.position.x;
      const top = node.position.y;
      const right = node.position.x + node.style.width;
      const bottom = node.position.y + node.style.height;

      return !(
        right < bounds.left ||
        left > bounds.right ||
        bottom < bounds.top ||
        top > bounds.bottom
      );
    })
    .map((node) => node.data.graphNodeId)
    .filter((nodeId): nodeId is number => Number.isFinite(nodeId));
}

export function TaxonomyViewPage() {
  const [activeNodeId, setActiveNodeId] = useState<number | null>(null);
  const [flowViewport, setFlowViewport] = useState<FlowViewport>(
    DEFAULT_FLOW_VIEWPORT,
  );
  const [leafDetailCache, setLeafDetailCache] = useState<
    Record<number, TaxonomyLeafNodeDetailRecord>
  >({});

  const rootQuery = useTaxonomyRootViewQuery({
    enabled: activeNodeId === null,
  });
  const nodeQuery = useTaxonomyNodeViewQuery(activeNodeId ?? 0, {
    enabled: activeNodeId !== null,
  });

  const rootMode = activeNodeId === null;
  const activeQuery = rootMode ? rootQuery : nodeQuery;
  const breadcrumbs = rootMode ? [] : (nodeQuery.data?.breadcrumb ?? []);
  const activeLeafId =
    nodeQuery.data?.node_kind === "leaf"
      ? nodeQuery.data.current_node.id
      : null;

  useEffect(() => {
    if (activeLeafId === null) {
      setLeafDetailCache({});
      setFlowViewport(DEFAULT_FLOW_VIEWPORT);
      return;
    }

    setLeafDetailCache({});
    setFlowViewport(DEFAULT_FLOW_VIEWPORT);
  }, [activeLeafId]);

  const leafSkeletonLayout = useMemo(() => {
    if (nodeQuery.data?.node_kind !== "leaf") {
      return null;
    }

    return buildLeafLayout({
      center: LAYOUT_CENTER,
      edges: nodeQuery.data.edges,
      hydratedNodeDetailsById: {},
      nodes: nodeQuery.data.nodes,
      viewport: BRANCH_LAYOUT_VIEWPORT,
      visibleCardNodeIds: [],
    });
  }, [nodeQuery.data]);

  const visibleLeafNodeIds = useMemo(() => {
    if (!leafSkeletonLayout || flowViewport.zoom < LEAF_CARD_ACTIVATION_ZOOM) {
      return [];
    }

    return selectLeafHydrationNodeIds(
      leafSkeletonLayout.nodes,
      flowViewport,
      BRANCH_LAYOUT_VIEWPORT,
    );
  }, [flowViewport, leafSkeletonLayout]);

  const missingLeafNodeIds = useMemo(
    () =>
      visibleLeafNodeIds.filter(
        (nodeId) => leafDetailCache[nodeId] === undefined,
      ),
    [leafDetailCache, visibleLeafNodeIds],
  );

  const leafDetailsQuery = useTaxonomyLeafNodeDetailsQuery(
    activeLeafId ?? 0,
    missingLeafNodeIds,
    {
      enabled:
        activeLeafId !== null &&
        flowViewport.zoom >= LEAF_CARD_ACTIVATION_ZOOM &&
        missingLeafNodeIds.length > 0,
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

  const leafHydratedNodeDetailsById = useMemo<
    Partial<Record<number, LeafHydratedNodeLayoutInput>>
  >(() => {
    if (nodeQuery.data?.node_kind !== "leaf") {
      return {};
    }

    const scopeByNodeId = new Map(
      nodeQuery.data.nodes.map((node) => [node.id, node.scope] as const),
    );
    const hydratedDetailsById: Partial<
      Record<number, LeafHydratedNodeLayoutInput>
    > = {};

    for (const [nodeIdKey, detail] of Object.entries(leafDetailCache)) {
      const nodeId = Number(nodeIdKey);
      const scope = scopeByNodeId.get(nodeId);

      if (!scope) {
        continue;
      }

      hydratedDetailsById[nodeId] = {
        ...detail,
        scope,
      };
    }

    return hydratedDetailsById;
  }, [leafDetailCache, nodeQuery.data]);

  const flowGraph = useMemo(() => {
    if (activeQuery.isPending) {
      return { edges: [] as Edge[], nodes: [] as BubbleFlowNode[] };
    }

    if (rootMode) {
      const branchLayout = buildBranchLayout({
        center: LAYOUT_CENTER,
        children: rootQuery.data?.children ?? [],
        viewport: BRANCH_LAYOUT_VIEWPORT,
      });

      return {
        edges: [] as Edge[],
        nodes: branchLayout.nodes.map(toFlowNode),
      };
    }

    if (nodeQuery.data?.node_kind === "leaf") {
      const leafLayout = buildLeafLayout({
        center: LAYOUT_CENTER,
        edges: nodeQuery.data.edges,
        hydratedNodeDetailsById: leafHydratedNodeDetailsById,
        nodes: nodeQuery.data.nodes,
        viewport: BRANCH_LAYOUT_VIEWPORT,
        visibleCardNodeIds: visibleLeafNodeIds,
      });

      return {
        edges: leafLayout.edges.map(toFlowEdge),
        nodes: leafLayout.nodes.map(toFlowNode),
      };
    }

    const branchLayout = buildBranchLayout({
      center: LAYOUT_CENTER,
      children: nodeQuery.data?.children ?? [],
      viewport: BRANCH_LAYOUT_VIEWPORT,
    });

    return {
      edges: [] as Edge[],
      nodes: branchLayout.nodes.map(toFlowNode),
    };
  }, [
    activeQuery.isPending,
    leafHydratedNodeDetailsById,
    nodeQuery.data,
    rootMode,
    rootQuery.data?.children,
    visibleLeafNodeIds,
  ]);

  return (
    <main
      className="flex min-h-screen flex-col gap-6 p-6"
      data-testid="taxonomy-shell-body"
    >
      <header
        className="grid min-h-16 grid-cols-[auto_1fr_auto] items-stretch gap-2.5 max-md:grid-cols-1"
        data-testid="taxonomy-header-shell"
      >
        <div className="inline-grid grid-cols-[auto_auto] items-stretch gap-2.5">
          <div aria-hidden="true" className="h-16 w-16 shrink-0 bg-[#30CBFF]" />
          <span className="inline-flex items-center px-2.5 py-2 text-[14px] leading-5 text-black">
            Knowledge Graph
          </span>
        </div>
        <div aria-hidden="true" className="min-w-0" />
        <div className="flex items-center justify-end gap-2.5 max-md:justify-start">
          <button
            className="min-h-10 min-w-[85px] cursor-not-allowed rounded-lg bg-[#171717] px-6 py-2.5 text-[14px] leading-5 font-medium text-[#FAFAFA] outline-offset-2 focus-visible:outline-2 focus-visible:outline-[#2563EB] disabled:bg-[#171717] disabled:text-[#FAFAFA]"
            disabled
            type="button"
          >
            GitHub
          </button>
          <button
            className="min-h-10 min-w-[85px] cursor-not-allowed rounded-lg bg-[#171717] px-6 py-2.5 text-[14px] leading-5 font-medium text-[#FAFAFA] outline-offset-2 focus-visible:outline-2 focus-visible:outline-[#2563EB] disabled:bg-[#171717] disabled:text-[#FAFAFA]"
            disabled
            type="button"
          >
            Login
          </button>
        </div>
      </header>
      <section
        aria-label="taxonomy flow canvas"
        className="relative min-h-[32rem] h-[calc(100vh-136px)] flex-1"
        data-testid="taxonomy-canvas-shell"
      >
        <div
          className="absolute inset-0 overflow-hidden rounded-[32px] border border-[rgba(214,227,247,0.86)] bg-[linear-gradient(137.03deg,rgba(254,254,255,1)_14.099%,rgba(245,249,255,1)_45.692%,rgba(249,251,255,1)_85.901%)] shadow-[0px_18px_52px_0px_rgba(107,133,189,0.09)]"
          data-testid="taxonomy-canvas-panel"
        >
          <nav
            aria-label="taxonomy breadcrumb"
            className="absolute top-[27px] left-[33px] z-20 flex max-w-[calc(100%-66px)] flex-wrap items-center justify-center gap-2 overflow-hidden"
            data-breadcrumb-style="inline-text"
            data-testid="taxonomy-breadcrumb-overlay"
          >
            <button
              aria-current={rootMode ? "page" : undefined}
              className={
                rootMode ? breadcrumbCurrentClasses : breadcrumbMutedClasses
              }
              onClick={() => {
                startTransition(() => setActiveNodeId(null));
              }}
              type="button"
            >
              Root
            </button>
            {breadcrumbs.flatMap((item) => [
              <span
                aria-hidden="true"
                className="text-[12px] leading-[18px] font-normal text-[rgba(117,133,161,0.56)]"
                key={`${item.id}-separator`}
              >
                /
              </span>,
              <button
                aria-current={
                  item.id === breadcrumbs.at(-1)?.id ? "page" : undefined
                }
                className={
                  item.id === breadcrumbs.at(-1)?.id
                    ? breadcrumbCurrentClasses
                    : breadcrumbMutedClasses
                }
                key={item.id}
                onClick={() => {
                  startTransition(() => setActiveNodeId(item.id));
                }}
                type="button"
              >
                {item.name}
              </button>,
            ])}
          </nav>
          {activeQuery.isPending ? (
            <section
              aria-busy="true"
              aria-live="polite"
              className="absolute top-1/2 left-1/2 z-20 w-[min(420px,calc(100%-40px))] -translate-x-1/2 -translate-y-1/2 rounded-[20px] border border-[rgba(148,163,184,0.24)] bg-[rgba(255,255,255,0.94)] p-[22px] text-left shadow-[0_18px_40px_rgba(15,23,42,0.14)]"
              data-testid="taxonomy-loading-overlay"
            >
              <h2 className="m-0 text-[1.1rem] text-[#0F172A]">
                Loading taxonomy view
              </h2>
              <p className="mt-2.5 mb-0 text-[#475569]">
                Fetching the latest taxonomy hierarchy snapshot from API.
              </p>
            </section>
          ) : null}
          {activeQuery.isError ? (
            <section
              className="absolute top-1/2 left-1/2 z-20 w-[min(420px,calc(100%-40px))] -translate-x-1/2 -translate-y-1/2 rounded-[20px] border border-[rgba(148,163,184,0.24)] bg-[rgba(255,255,255,0.94)] p-[22px] text-left shadow-[0_18px_40px_rgba(15,23,42,0.14)]"
              data-testid="taxonomy-error-overlay"
              role="alert"
            >
              <h2 className="m-0 text-[1.1rem] text-[#0F172A]">
                Taxonomy view unavailable
              </h2>
              <p className="mt-2.5 mb-0 text-[#475569]">
                {activeQuery.error.message}
              </p>
            </section>
          ) : null}
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
          <div className="taxonomy-flow-shell">
            <ReactFlow
              edges={flowGraph.edges}
              fitView
              fitViewOptions={{ padding: 0.18 }}
              key={activeNodeId ?? "root"}
              minZoom={0.2}
              nodeTypes={nodeTypes}
              nodes={flowGraph.nodes}
              onMoveEnd={(_, viewport) => {
                setFlowViewport(viewport);
              }}
              onNodeClick={(_, node) => {
                const targetNodeId = node.data.targetNodeId;
                if (typeof targetNodeId !== "number") {
                  return;
                }
                startTransition(() => setActiveNodeId(targetNodeId));
              }}
              proOptions={{ hideAttribution: true }}
            >
              <Background />
            </ReactFlow>
          </div>
        </div>
      </section>
    </main>
  );
}
