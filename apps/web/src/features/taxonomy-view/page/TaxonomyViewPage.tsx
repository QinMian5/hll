// abstract: Taxonomy-query-driven React Flow page with click drill-down interactions.
// out_of_scope: Backend taxonomy read orchestration and graph-edge rendering behaviors.

import "@xyflow/react/dist/style.css";

import {
  Background,
  type Node,
  type NodeProps,
  ReactFlow,
} from "@xyflow/react";
import { startTransition, useState } from "react";

import {
  useTaxonomyNodeViewQuery,
  useTaxonomyRootViewQuery,
} from "../data/taxonomyViewQueries";

interface BranchChildItem {
  readonly depth: number;
  readonly descendant_card_count: number;
  readonly id: number;
  readonly name: string;
}

interface LeafNodeItem {
  readonly id: number;
  readonly scope: "inner" | "outer";
  readonly title: string;
}

type BubbleNodeData = Record<string, unknown> & {
  readonly depth: number;
  readonly label: string;
  readonly scope: "branch" | "inner" | "outer";
  readonly targetNodeId: number | null;
  readonly tooltip: string;
};

type BubbleNode = Node<BubbleNodeData, "bubble">;

function TaxonomyBubbleNode({ data }: NodeProps<BubbleNode>) {
  const isBranch = data.scope === "branch";

  return (
    <div
      className={`taxonomy-bubble taxonomy-bubble--${data.scope}`}
      data-depth={data.depth}
      title={data.tooltip}
    >
      <span className="taxonomy-bubble__label">{data.label}</span>
      {isBranch ? <span className="taxonomy-bubble__hint">Open</span> : null}
    </div>
  );
}

const nodeTypes = {
  bubble: TaxonomyBubbleNode,
};

function bubbleDiameterFromDescendantCount(
  descendantCardCount: number,
): number {
  const scaled = 44 + Math.log(Math.max(descendantCardCount, 1) + 1) * 28;
  return Math.max(44, Math.min(Math.round(scaled), 120));
}

function layoutAsRadialGrid(options: {
  readonly diameterForIndex: (index: number) => number;
  readonly items: number;
}): Array<{ readonly x: number; readonly y: number }> {
  if (options.items <= 0) {
    return [];
  }

  const points: Array<{ readonly x: number; readonly y: number }> = [];
  const step = (2 * Math.PI) / options.items;
  for (let index = 0; index < options.items; index += 1) {
    const angle = step * index;
    const radius = 160 + options.diameterForIndex(index) * 0.8;
    points.push({
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    });
  }
  return points;
}

function buildBranchNodes(children: readonly BranchChildItem[]): BubbleNode[] {
  const positions = layoutAsRadialGrid({
    diameterForIndex: (index) =>
      bubbleDiameterFromDescendantCount(
        children[index]?.descendant_card_count ?? 1,
      ),
    items: children.length,
  });

  return children.map((child, index) => {
    const diameter = bubbleDiameterFromDescendantCount(
      child.descendant_card_count,
    );
    return {
      data: {
        depth: child.depth,
        label: child.name,
        scope: "branch",
        targetNodeId: child.id,
        tooltip: `${child.name} · ${child.descendant_card_count} cards`,
      },
      draggable: false,
      id: `taxonomy-${child.id}`,
      position: positions[index] ?? { x: 0, y: 0 },
      selectable: false,
      style: {
        borderRadius: `${diameter}px`,
        height: diameter,
        width: diameter,
      },
      type: "bubble",
    };
  });
}

function buildLeafNodes(nodes: readonly LeafNodeItem[]): BubbleNode[] {
  const positions = layoutAsRadialGrid({
    diameterForIndex: () => 64,
    items: nodes.length,
  });

  return nodes.map((node, index) => {
    const diameter = node.scope === "inner" ? 68 : 52;
    return {
      data: {
        depth: 0,
        label: node.title,
        scope: node.scope,
        targetNodeId: null,
        tooltip: node.title,
      },
      draggable: false,
      id: `card-${node.id}`,
      position: positions[index] ?? { x: 0, y: 0 },
      selectable: false,
      style: {
        borderRadius: `${diameter}px`,
        height: diameter,
        width: diameter,
      },
      type: "bubble",
    };
  });
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
  const flowNodes = activeQuery.isPending
    ? []
    : rootMode
      ? buildBranchNodes(rootQuery.data?.children ?? [])
      : nodeQuery.data?.node_kind === "leaf"
        ? buildLeafNodes(nodeQuery.data.nodes)
        : buildBranchNodes(nodeQuery.data?.children ?? []);

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
            edges={[]}
            fitView
            minZoom={0.2}
            nodeTypes={nodeTypes}
            nodes={flowNodes}
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
