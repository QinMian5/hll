// abstract: Force-based branch layout helper for weighted taxonomy bubbles.
// out_of_scope: Leaf graph layout and React Flow page orchestration.

import {
  forceCenter,
  forceCollide,
  forceRadial,
  forceSimulation,
} from "d3-force";
import type {
  BranchLayoutInput,
  BranchLayoutResult,
  LayoutPoint,
} from "./taxonomyLayoutTypes";

interface BranchSimulationNode {
  readonly child: BranchLayoutInput["children"][number];
  readonly diameter: number;
  readonly id: string;
  readonly radius: number;
  readonly targetRadius: number;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
}

export function bubbleDiameterFromDescendantCount(
  descendantCardCount: number,
): number {
  const scaled = 44 + Math.log(Math.max(descendantCardCount, 1) + 1) * 28;
  return Math.max(44, Math.min(Math.round(scaled), 120));
}

function positionOnRing(options: {
  readonly center: LayoutPoint;
  readonly index: number;
  readonly targetRadius: number;
}): LayoutPoint {
  const angle = options.index * 2.399963229728653;
  const radius = options.targetRadius;

  return {
    x: options.center.x + Math.cos(angle) * radius,
    y: options.center.y + Math.sin(angle) * radius,
  };
}

function clampPosition(options: {
  readonly center: LayoutPoint;
  readonly node: BranchSimulationNode;
  readonly viewport: BranchLayoutInput["viewport"];
}): LayoutPoint {
  const padding = options.node.radius + 24;

  return {
    x: Math.min(
      Math.max(options.node.x, padding),
      options.viewport.width - padding,
    ),
    y: Math.min(
      Math.max(options.node.y, padding),
      options.viewport.height - padding,
    ),
  };
}

export function buildBranchLayout(
  input: BranchLayoutInput,
): BranchLayoutResult {
  const sortedChildren = [...input.children].sort(
    (left, right) =>
      right.descendant_card_count - left.descendant_card_count ||
      left.id - right.id,
  );

  const nodes: BranchSimulationNode[] = sortedChildren.map((child, index) => {
    const diameter = bubbleDiameterFromDescendantCount(
      child.descendant_card_count,
    );
    const radius = diameter / 2;
    const targetRadius =
      index === 0 ? 0 : Math.min(110 + Math.sqrt(index) * 118, 360);
    const position = positionOnRing({
      center: input.center,
      index,
      targetRadius,
    });

    return {
      child,
      diameter,
      id: `taxonomy-${child.id}`,
      radius,
      targetRadius,
      x: position.x,
      y: position.y,
    };
  });

  forceSimulation(nodes)
    .force("center", forceCenter(input.center.x, input.center.y).strength(0.08))
    .force(
      "collide",
      forceCollide<BranchSimulationNode>()
        .radius((node) => node.radius + 12)
        .strength(1),
    )
    .force(
      "radial",
      forceRadial<BranchSimulationNode>(
        (node) => node.targetRadius,
        input.center.x,
        input.center.y,
      ).strength(0.22),
    )
    .stop()
    .tick(220);

  return {
    nodes: nodes.map((node) => ({
      data: {
        depth: node.child.depth,
        label: node.child.name,
        scope: "branch",
        targetNodeId: node.child.id,
        tooltip: `${node.child.name} · ${node.child.descendant_card_count} cards`,
      },
      id: node.id,
      position: clampPosition({
        center: input.center,
        node,
        viewport: input.viewport,
      }),
      style: {
        borderRadius: `${node.diameter}px`,
        height: node.diameter,
        width: node.diameter,
      },
      type: "bubble",
    })),
  };
}
