// abstract: Taxonomy-query-driven React Flow page with dedicated branch and leaf layouts.
// out_of_scope: Backend taxonomy read orchestration and page-shell redesign.

import "@xyflow/react/dist/style.css";

import { Background, type Edge, type Node, ReactFlow } from "@xyflow/react";
import { startTransition, useMemo, useState } from "react";
import {
  useTaxonomyNodeViewQuery,
  useTaxonomyRootViewQuery,
} from "../data/taxonomyViewQueries";
import { buildBranchLayout } from "./layout/buildBranchLayout";
import { buildLeafLayout } from "./layout/buildLeafLayout";
import type { TaxonomyLayoutNodeData } from "./layout/taxonomyLayoutTypes";
import { TaxonomyFlowNode } from "./TaxonomyFlowNode";

const BRANCH_LAYOUT_VIEWPORT = { height: 900, width: 1404 };
const LAYOUT_CENTER = { x: 702, y: 450 };

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;

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
    id: edge.id,
    source: edge.source,
    target: edge.target,
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
        nodes: nodeQuery.data.nodes,
        viewport: BRANCH_LAYOUT_VIEWPORT,
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
    nodeQuery.data,
    rootMode,
    rootQuery.data?.children,
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
              className="text-[13px] leading-[18px] font-normal text-[rgba(92,107,138,0.74)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0"
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
                className="text-[13px] leading-[18px] font-medium text-[rgba(33,43,64,0.96)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0"
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
          <div className="taxonomy-flow-shell">
            <ReactFlow
              edges={flowGraph.edges}
              fitView
              fitViewOptions={{ padding: 0.18 }}
              key={activeNodeId ?? "root"}
              minZoom={0.2}
              nodeTypes={nodeTypes}
              nodes={flowGraph.nodes}
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
