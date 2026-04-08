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
  readonly content: string;
  readonly diameter: number;
  readonly id: string;
  readonly scope: "inner" | "outer";
  readonly title: string;
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

export function buildLeafLayout(input: LeafLayoutInput): LeafLayoutResult {
  const sortedNodes = [...input.nodes].sort(
    (left, right) => left.id - right.id,
  );
  const simulationNodes: LeafSimulationNode[] = sortedNodes.map(
    (node, index) => {
      const position = positionOnSpiral({
        center: input.center,
        index,
      });

      return {
        content: node.content,
        diameter: leafNodeDiameter(node.scope),
        id: `card-${node.id}`,
        scope: node.scope,
        title: node.title,
        x: position.x,
        y: position.y,
      };
    },
  );

  const nodeIds = new Set(simulationNodes.map((node) => node.id));
  const linkEdges = input.edges.map((edge) => {
    const source = `card-${edge.source_node_id}`;
    const target = `card-${edge.target_node_id}`;

    if (!nodeIds.has(source) || !nodeIds.has(target)) {
      throw new Error(`Leaf edge ${edge.id} references an unknown node.`);
    }

    return {
      source,
      strength: edge.strength,
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
      id: edge.id,
      source: `card-${edge.source_node_id}`,
      target: `card-${edge.target_node_id}`,
    })),
    nodes: simulationNodes.map((node) => ({
      data: {
        content: node.content,
        depth: 0,
        label: node.title,
        scope: node.scope,
        targetNodeId: null,
        tooltip: node.title,
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
    })),
  };
}
