// abstract: Force-based leaf layout helper for title-first taxonomy graph nodes.
// out_of_scope: Hover-disclosure UI wiring and page-level React Flow orchestration.

import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
} from "d3-force";

import type {
  LayoutPoint,
  LeafLayoutInput,
  LeafLayoutResult,
} from "./taxonomyLayoutTypes";

interface LeafSimulationNode {
  readonly diameter: number;
  readonly graphNodeId: number;
  readonly id: string;
  readonly scope: "inner" | "outer";
  x: number;
  y: number;
  vx?: number;
  vy?: number;
}

function positionOnSpiral(options: {
  readonly center: LayoutPoint;
  readonly index: number;
}): LayoutPoint {
  const angle = options.index * 2.399963229728653;
  const radius = 80 + Math.sqrt(options.index + 1) * 72;

  return {
    x: options.center.x + Math.cos(angle) * radius,
    y: options.center.y + Math.sin(angle) * radius,
  };
}

function leafNodeDiameter(scope: "inner" | "outer") {
  return scope === "inner" ? 68 : 52;
}

function pointNodeDiameter() {
  return 12;
}

export function buildLeafLayout(input: LeafLayoutInput): LeafLayoutResult {
  const hydratedNodeDetailsById = input.hydratedNodeDetailsById ?? {};
  const visibleBubbleNodeIds = new Set(input.visibleBubbleNodeIds ?? []);
  const sortedNodes = [...input.nodes].sort(
    (left, right) => left.id - right.id,
  );
  const simulationNodes: LeafSimulationNode[] = sortedNodes.map(
    (node, index) => {
      const position = positionOnSpiral({
        center: input.center,
        index,
      });

      const shouldRenderBubble =
        visibleBubbleNodeIds.has(node.id) &&
        input.hydratedNodeDetailsById?.[node.id] !== undefined;

      return {
        diameter: shouldRenderBubble
          ? leafNodeDiameter(node.scope)
          : pointNodeDiameter(),
        graphNodeId: node.id,
        id: `card-${node.id}`,
        scope: node.scope,
        x: position.x,
        y: position.y,
      };
    },
  );

  const nodeIds = new Set(simulationNodes.map((node) => node.id));
  const linkEdges = input.edges.map((edge) => {
    const [sourceNodeId, targetNodeId, strength] = edge;
    const source = `card-${sourceNodeId}`;
    const target = `card-${targetNodeId}`;

    if (!nodeIds.has(source) || !nodeIds.has(target)) {
      throw new Error(
        `Leaf edge ${sourceNodeId}:${targetNodeId} references an unknown node.`,
      );
    }

    return {
      source,
      strength,
      target,
    };
  });

  forceSimulation(simulationNodes)
    .force(
      "link",
      forceLink<
        LeafSimulationNode,
        {
          readonly source: string;
          readonly strength: number;
          readonly target: string;
        }
      >(linkEdges)
        .id((node) => node.id)
        .distance((edge) => 130 - edge.strength * 24)
        .strength((edge) => 0.25 + edge.strength * 0.2),
    )
    .force("charge", forceManyBody<LeafSimulationNode>().strength(-240))
    .force(
      "collide",
      forceCollide<LeafSimulationNode>()
        .radius((node) => node.diameter / 2 + 10)
        .strength(1),
    )
    .force("center", forceCenter(input.center.x, input.center.y).strength(0.12))
    .stop()
    .tick(220);

  return {
    edges: input.edges.map((edge) => ({
      id: `${edge[0]}:${edge[1]}`,
      source: `card-${edge[0]}`,
      target: `card-${edge[1]}`,
    })),
    nodes: simulationNodes.map((node) => {
      const hydratedDetails = hydratedNodeDetailsById[node.graphNodeId];
      const shouldRenderBubble =
        visibleBubbleNodeIds.has(node.graphNodeId) &&
        hydratedDetails !== undefined;

      return {
        data: {
          content: shouldRenderBubble ? hydratedDetails.content : undefined,
          depth: 0,
          graphNodeId: node.graphNodeId,
          label: shouldRenderBubble ? hydratedDetails.title : "",
          renderMode: shouldRenderBubble ? "bubble" : "point",
          scope: node.scope,
          targetNodeId: null,
          tooltip: shouldRenderBubble ? hydratedDetails.title : "",
        },
        id: node.id,
        position: {
          x: node.x,
          y: node.y,
        },
        style: {
          borderRadius: `${node.diameter}px`,
          height: node.diameter,
          width: node.diameter,
        },
        type: "bubble",
      };
    }),
  };
}
