// abstract: Force-based branch layout helper for weighted taxonomy bubbles.
// out_of_scope: Leaf graph layout and React Flow page orchestration.

import {
  forceCenter,
  forceCollide,
  forceSimulation,
  forceX,
  forceY,
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
  readonly targetX: number;
  readonly targetY: number;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
}

export function bubbleDiameterFromDescendantCount(
  descendantCardCount: number,
): number {
  const scaled = 100 + Math.log(Math.max(descendantCardCount, 1)) * 20;
  return Math.round(Math.max(100, scaled));
}

function positionOnRing(options: {
  readonly center: LayoutPoint;
  readonly index: number;
  readonly targetRadius: number;
}): LayoutPoint {
  const angle = options.index * 2.399963229728653;
  const radius = options.targetRadius;

  return {
    x: options.center.x + Math.cos(angle) * radius * 1.18,
    y: options.center.y + Math.sin(angle) * radius * 0.72,
  };
}

function clampPosition(options: {
  readonly center: LayoutPoint;
  readonly node: BranchSimulationNode;
  readonly viewport: BranchLayoutInput["viewport"];
}): LayoutPoint {
  const padding = options.node.radius + 32;

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

function resolveBranchOverlaps(options: {
  readonly center: LayoutPoint;
  readonly nodes: BranchSimulationNode[];
  readonly viewport: BranchLayoutInput["viewport"];
}) {
  for (let pass = 0; pass < 80; pass += 1) {
    let moved = false;

    for (let leftIndex = 0; leftIndex < options.nodes.length; leftIndex += 1) {
      const left = options.nodes[leftIndex];

      for (
        let rightIndex = leftIndex + 1;
        rightIndex < options.nodes.length;
        rightIndex += 1
      ) {
        const right = options.nodes[rightIndex];
        const deltaX = right.x - left.x;
        const deltaY = right.y - left.y;
        const distance = Math.hypot(deltaX, deltaY);
        const minimumDistance = left.radius + right.radius + 8;

        if (distance >= minimumDistance) {
          continue;
        }

        const angle =
          distance > 0
            ? Math.atan2(deltaY, deltaX)
            : (leftIndex + 1) * 2.399963229728653;
        const pushDistance = (minimumDistance - Math.max(distance, 0.001)) / 2;
        const leftMobility = left.targetRadius === 0 ? 0.2 : 1;
        const rightMobility = right.targetRadius === 0 ? 0.2 : 1;
        const totalMobility = leftMobility + rightMobility;
        const unitX = Math.cos(angle);
        const unitY = Math.sin(angle);

        left.x -= unitX * pushDistance * (rightMobility / totalMobility);
        left.y -= unitY * pushDistance * (rightMobility / totalMobility);
        right.x += unitX * pushDistance * (leftMobility / totalMobility);
        right.y += unitY * pushDistance * (leftMobility / totalMobility);

        const clampedLeft = clampPosition({
          center: options.center,
          node: left,
          viewport: options.viewport,
        });
        const clampedRight = clampPosition({
          center: options.center,
          node: right,
          viewport: options.viewport,
        });

        left.x = clampedLeft.x;
        left.y = clampedLeft.y;
        right.x = clampedRight.x;
        right.y = clampedRight.y;
        moved = true;
      }
    }

    if (!moved) {
      break;
    }
  }
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
      index === 0 ? 0 : Math.min(160 + Math.sqrt(index) * 150, 430);
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
      targetX: position.x,
      targetY: position.y,
      x: position.x,
      y: position.y,
    };
  });

  forceSimulation(nodes)
    .force("center", forceCenter(input.center.x, input.center.y).strength(0.08))
    .force(
      "collide",
      forceCollide<BranchSimulationNode>()
        .radius((node) => node.radius + 16)
        .strength(1),
    )
    .force(
      "x",
      forceX<BranchSimulationNode>((node) => node.targetX).strength(0.3),
    )
    .force(
      "y",
      forceY<BranchSimulationNode>((node) => node.targetY).strength(0.24),
    )
    .stop()
    .tick(260);

  resolveBranchOverlaps({
    center: input.center,
    nodes,
    viewport: input.viewport,
  });

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
