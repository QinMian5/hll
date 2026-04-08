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
    <main className="taxonomy-view-shell">
      <header className="taxonomy-header" data-testid="taxonomy-header-shell">
        <div className="taxonomy-header__brand">
          <div aria-hidden="true" className="taxonomy-header__brand-mark" />
          <span className="taxonomy-header__brand-name">Knowledge Graph</span>
        </div>
        <div aria-hidden="true" className="taxonomy-header__spacer" />
        <div className="taxonomy-header__actions">
          <button className="taxonomy-header__action" disabled type="button">
            GitHub
          </button>
          <button className="taxonomy-header__action" disabled type="button">
            Login
          </button>
        </div>
      </header>
      <section
        aria-label="taxonomy flow canvas"
        className="taxonomy-canvas-shell"
        data-testid="taxonomy-canvas-shell"
      >
        <nav
          aria-label="taxonomy breadcrumb"
          className="taxonomy-breadcrumb taxonomy-canvas-overlay"
          data-testid="taxonomy-breadcrumb-overlay"
        >
          <button
            className="taxonomy-breadcrumb__item"
            onClick={() => {
              startTransition(() => setActiveNodeId(null));
            }}
            type="button"
          >
            Root
          </button>
          {breadcrumbs.map((item) => (
            <button
              className="taxonomy-breadcrumb__item"
              key={item.id}
              onClick={() => {
                startTransition(() => setActiveNodeId(item.id));
              }}
              type="button"
            >
              {item.name}
            </button>
          ))}
        </nav>
        {activeQuery.isPending ? (
          <section
            aria-busy="true"
            aria-live="polite"
            className="taxonomy-status-overlay taxonomy-canvas-overlay"
            data-testid="taxonomy-loading-overlay"
          >
            <h2>Loading taxonomy view</h2>
            <p>Fetching the latest taxonomy hierarchy snapshot from API.</p>
          </section>
        ) : null}
        {activeQuery.isError ? (
          <section
            className="taxonomy-status-overlay taxonomy-canvas-overlay"
            data-testid="taxonomy-error-overlay"
            role="alert"
          >
            <h2>Taxonomy view unavailable</h2>
            <p>{activeQuery.error.message}</p>
          </section>
        ) : null}
        <div className="taxonomy-flow-shell">
          <ReactFlow
            edges={flowGraph.edges}
            fitView
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
      </section>
    </main>
  );
}
