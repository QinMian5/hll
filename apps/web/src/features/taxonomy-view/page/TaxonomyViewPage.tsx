// abstract: Taxonomy-query-driven page shell that routes branch rendering to React Flow and leaf rendering to deck.gl.
// out_of_scope: Backend taxonomy read orchestration and deck.gl scene internals.

import "@xyflow/react/dist/style.css";

import { type Node, ReactFlow } from "@xyflow/react";
import { lazy, Suspense, startTransition, useMemo, useState } from "react";

import {
  useTaxonomyNodeViewQuery,
  useTaxonomyRootViewQuery,
} from "../data/taxonomyViewQueries";

export {
  LEAF_CARD_ACTIVATION_ZOOM,
  LEAF_HYDRATION_OVERSCAN,
} from "./leaf/leafRendererConfig";

import { buildBranchLayout } from "./layout/buildBranchLayout";
import type { TaxonomyLayoutNodeData } from "./layout/taxonomyLayoutTypes";
import { TaxonomyFlowNode } from "./TaxonomyFlowNode";

const BRANCH_LAYOUT_VIEWPORT = { height: 900, width: 1404 };
const LAYOUT_CENTER = { x: 702, y: 450 };
const breadcrumbMutedClasses =
  "text-[13px] leading-[18px] font-normal text-[rgba(92,107,138,0.74)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0";
const breadcrumbCurrentClasses =
  "text-[13px] leading-[18px] font-medium text-[rgba(33,43,64,0.96)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0";

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;

const nodeTypes = {
  bubble: TaxonomyFlowNode,
};

const LeafRenderer = lazy(() =>
  import("./leaf/LeafRenderer").then((module) => ({
    default: module.LeafRenderer,
  })),
);

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

export function TaxonomyViewPage() {
  const [activeNodeId, setActiveNodeId] = useState<number | null>(null);

  const rootQuery = useTaxonomyRootViewQuery({
    enabled: activeNodeId === null,
  });
  const nodeQuery = useTaxonomyNodeViewQuery(activeNodeId ?? 0, {
    enabled: activeNodeId !== null,
  });

  const rootMode = activeNodeId === null;
  const activeQuery = rootMode ? rootQuery : nodeQuery;
  const breadcrumbs = rootMode ? [] : (nodeQuery.data?.breadcrumb ?? []);

  const branchFlowGraph = useMemo(() => {
    if (activeQuery.isPending) {
      return { nodes: [] as BubbleFlowNode[] };
    }

    if (rootMode) {
      const branchLayout = buildBranchLayout({
        center: LAYOUT_CENTER,
        children: rootQuery.data?.children ?? [],
        viewport: BRANCH_LAYOUT_VIEWPORT,
      });

      return {
        nodes: branchLayout.nodes.map(toFlowNode),
      };
    }

    const branchLayout = buildBranchLayout({
      center: LAYOUT_CENTER,
      children:
        nodeQuery.data?.node_kind === "branch" ? nodeQuery.data.children : [],
      viewport: BRANCH_LAYOUT_VIEWPORT,
    });

    return {
      nodes: branchLayout.nodes.map(toFlowNode),
    };
  }, [
    activeQuery.isPending,
    nodeQuery.data,
    rootMode,
    rootQuery.data?.children,
  ]);

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden p-6"
      data-testid="taxonomy-shell-body"
    >
      <section
        aria-label="taxonomy flow canvas"
        className="relative min-h-0 flex-1"
        data-testid="taxonomy-canvas-shell"
      >
        <div
          className="absolute inset-0 overflow-hidden rounded-[32px] border border-[rgba(214,227,247,0.86)] bg-[linear-gradient(137.03deg,rgba(254,254,255,1)_14.099%,rgba(245,249,255,1)_45.692%,rgba(249,251,255,1)_85.901%)] shadow-[0_18px_52px_rgba(107,133,189,0.09)]"
          data-testid="taxonomy-canvas-panel"
        >
          <nav
            aria-label="taxonomy breadcrumb"
            className="absolute top-[27px] left-[33px] z-20 flex max-w-[calc(100%-66px)] flex-wrap items-center justify-center gap-2"
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
          <div className="taxonomy-flow-shell absolute inset-0 overflow-hidden rounded-[32px]">
            {nodeQuery.data?.node_kind === "leaf" ? (
              <Suspense fallback={null}>
                <LeafRenderer
                  center={LAYOUT_CENTER}
                  key={nodeQuery.data.current_node.id}
                  leafView={nodeQuery.data}
                  viewport={BRANCH_LAYOUT_VIEWPORT}
                />
              </Suspense>
            ) : (
              <div
                className="h-full w-full"
                data-testid="taxonomy-branch-reactflow"
              >
                <ReactFlow
                  fitView
                  fitViewOptions={{ padding: 0.24 }}
                  key={activeNodeId ?? "root"}
                  minZoom={0.2}
                  nodeTypes={nodeTypes}
                  nodes={branchFlowGraph.nodes}
                  onNodeClick={(_, node) => {
                    const targetNodeId = node.data.targetNodeId;
                    if (typeof targetNodeId !== "number") {
                      return;
                    }
                    startTransition(() => setActiveNodeId(targetNodeId));
                  }}
                  proOptions={{ hideAttribution: true }}
                ></ReactFlow>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
