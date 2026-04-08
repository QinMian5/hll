// abstract: Deterministic placeholder leaf layout helper for title-first taxonomy graph nodes.
// out_of_scope: Final force-simulation tuning and hover-disclosure UI wiring.

import type {
  LayoutPoint,
  LeafLayoutInput,
  LeafLayoutResult,
} from "./taxonomyLayoutTypes";

function positionOnRing(options: {
  readonly center: LayoutPoint;
  readonly index: number;
  readonly items: number;
}): LayoutPoint {
  const angle = ((2 * Math.PI) / Math.max(options.items, 1)) * options.index;
  const radius = 160 + options.index * 10;

  return {
    x: options.center.x + Math.cos(angle) * radius,
    y: options.center.y + Math.sin(angle) * radius,
  };
}

export function buildLeafLayout(input: LeafLayoutInput): LeafLayoutResult {
  const sortedNodes = [...input.nodes].sort(
    (left, right) => left.id - right.id,
  );

  return {
    edges: input.edges.map((edge) => ({
      id: edge.id,
      source: `card-${edge.source_node_id}`,
      target: `card-${edge.target_node_id}`,
    })),
    nodes: sortedNodes.map((node, index) => {
      const diameter = node.scope === "inner" ? 68 : 52;

      return {
        data: {
          content: node.content,
          depth: 0,
          label: node.title,
          scope: node.scope,
          targetNodeId: null,
          tooltip: node.title,
        },
        id: `card-${node.id}`,
        position: positionOnRing({
          center: input.center,
          index,
          items: sortedNodes.length,
        }),
        style: {
          borderRadius: `${diameter}px`,
          height: diameter,
          width: diameter,
        },
        type: "bubble",
      };
    }),
  };
}
