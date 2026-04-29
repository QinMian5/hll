// abstract: Force-based leaf layout helper for point-only taxonomy graph nodes.
// out_of_scope: DOM title labels, disclosure content, and deck.gl interaction wiring.

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
  readonly graphNodeId: number;
  readonly id: string;
  readonly scope: "inner" | "outer";
  x: number;
  y: number;
  vx?: number;
  vy?: number;
}

export const LEAF_POINT_DIAMETER = 8;
export const LEAF_COLLISION_RADIUS = 10;

function positionOnSpiral(options: {
  readonly center: LayoutPoint;
  readonly index: number;
}): LayoutPoint {
  const angle = options.index * 2.399963229728653;
  const radius = 48 + Math.sqrt(options.index + 1) * 52;

  return {
    x: options.center.x + Math.cos(angle) * radius,
    y: options.center.y + Math.sin(angle) * radius,
  };
}

export function buildLeafLayout(input: LeafLayoutInput): LeafLayoutResult {
  const lockedNodeCentersById = input.lockedNodeCentersById;
  const sortedNodes = [...input.nodes].sort(
    (left, right) => left.id - right.id,
  );
  const simulationNodes: LeafSimulationNode[] = sortedNodes.map(
    (node, index) => {
      const lockedCenter = lockedNodeCentersById?.get(node.id);
      const position =
        lockedCenter ??
        positionOnSpiral({
          center: input.center,
          index,
        });

      return {
        graphNodeId: node.id,
        id: `leaf-${node.id}`,
        scope: node.scope,
        x: position.x,
        y: position.y,
      };
    },
  );

  const nodeIds = new Set(simulationNodes.map((node) => node.id));
  const linkEdges = input.edges.map((edge) => {
    const [sourceNodeId, targetNodeId, strength] = edge;
    const source = `leaf-${sourceNodeId}`;
    const target = `leaf-${targetNodeId}`;

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

  if (!lockedNodeCentersById) {
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
          .distance((edge) => 96 - edge.strength * 32)
          .strength((edge) => 0.38 + edge.strength * 0.34),
      )
      .force("charge", forceManyBody<LeafSimulationNode>().strength(-80))
      .force(
        "collide",
        forceCollide<LeafSimulationNode>()
          .radius(LEAF_COLLISION_RADIUS)
          .strength(1),
      )
      .force(
        "center",
        forceCenter(input.center.x, input.center.y).strength(0.12),
      )
      .stop()
      .tick(220);
  }

  return {
    edges: input.edges.map((edge) => ({
      id: `${edge[0]}:${edge[1]}`,
      source: `leaf-${edge[0]}`,
      target: `leaf-${edge[1]}`,
    })),
    nodes: simulationNodes.map((node) => {
      return {
        data: {
          depth: 0,
          graphNodeId: node.graphNodeId,
          label: "",
          renderMode: "point" as const,
          scope: node.scope,
          targetNodeId: null,
          tooltip: "",
        },
        id: node.id,
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
      };
    }),
  };
}
