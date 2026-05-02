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
  LayoutViewport,
} from "./taxonomyLayoutTypes";

export const BRANCH_DESKTOP_REFERENCE_VIEWPORT = {
  height: 1024,
  width: 1120,
} as const;

export const BRANCH_MOBILE_REFERENCE_VIEWPORT = {
  height: 892,
  width: 440,
} as const;

export interface BranchBubbleMetrics {
  readonly diameter: number;
  readonly labelFontSize: number;
  readonly labelLineHeight: number;
  readonly labelMaxWidth: number;
}

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
  viewport: LayoutViewport = BRANCH_DESKTOP_REFERENCE_VIEWPORT,
): number {
  return buildBranchBubbleMetrics(descendantCardCount, viewport).diameter;
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), maximum);
}

function lerp(start: number, end: number, amount: number) {
  return start + (end - start) * amount;
}

function viewportWidthFactor(viewport: LayoutViewport) {
  return clamp(
    (viewport.width - BRANCH_MOBILE_REFERENCE_VIEWPORT.width) /
      (BRANCH_DESKTOP_REFERENCE_VIEWPORT.width -
        BRANCH_MOBILE_REFERENCE_VIEWPORT.width),
    0,
    1,
  );
}

export function buildBranchBubbleMetrics(
  descendantCardCount: number,
  viewport: LayoutViewport,
): BranchBubbleMetrics {
  const logCount = Math.log10(Math.max(descendantCardCount, 10));
  const densityFactor = clamp((logCount - 1) / 2, 0, 1) ** 1.8;
  const viewportFactor = viewportWidthFactor(viewport);
  const desktopDiameter = lerp(146, 236, densityFactor);
  const mobileDiameter = lerp(100, 132, densityFactor);
  const diameter = Math.round(
    lerp(mobileDiameter, desktopDiameter, viewportFactor),
  );
  const labelFontSize = Math.round(lerp(13, 16, viewportFactor));

  return {
    diameter,
    labelFontSize,
    labelLineHeight: Math.round(labelFontSize * 1.14),
    labelMaxWidth: Math.round(diameter * 0.68),
  };
}

function positionOnRing(options: {
  readonly center: LayoutPoint;
  readonly index: number;
  readonly nodeRadius: number;
  readonly targetRadius: number;
  readonly viewport: BranchLayoutInput["viewport"];
}): LayoutPoint {
  const angle = options.index * 2.399963229728653;
  const radius = options.targetRadius;
  const viewportPadding = 16;
  const horizontalLimit = Math.max(
    options.nodeRadius,
    Math.min(options.center.x, options.viewport.width - options.center.x) -
      options.nodeRadius -
      viewportPadding,
  );
  const verticalLimit = Math.max(
    options.nodeRadius,
    Math.min(options.center.y, options.viewport.height - options.center.y) -
      options.nodeRadius -
      viewportPadding,
  );

  return {
    x:
      options.center.x +
      Math.cos(angle) * Math.min(radius * 1.05, horizontalLimit),
    y:
      options.center.y +
      Math.sin(angle) * Math.min(radius * 0.86, verticalLimit),
  };
}

function clampCenterPosition(options: {
  readonly center: LayoutPoint;
  readonly node: BranchSimulationNode;
  readonly viewport: BranchLayoutInput["viewport"];
}): LayoutPoint {
  const padding = options.node.radius + 12;

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
        const pushDistance = minimumDistance - Math.max(distance, 0.001);
        const leftMobility = left.targetRadius === 0 ? 0.2 : 1;
        const rightMobility = right.targetRadius === 0 ? 0.2 : 1;
        const totalMobility = leftMobility + rightMobility;
        const unitX = Math.cos(angle);
        const unitY = Math.sin(angle);

        left.x -= unitX * pushDistance * (rightMobility / totalMobility);
        left.y -= unitY * pushDistance * (rightMobility / totalMobility);
        right.x += unitX * pushDistance * (leftMobility / totalMobility);
        right.y += unitY * pushDistance * (leftMobility / totalMobility);

        const clampedLeft = clampCenterPosition({
          center: options.center,
          node: left,
          viewport: options.viewport,
        });
        const clampedRight = clampCenterPosition({
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
      left.name.localeCompare(right.name) ||
      left.route_path.localeCompare(right.route_path),
  );

  const nodes: BranchSimulationNode[] = sortedChildren.map((child, index) => {
    const metrics = buildBranchBubbleMetrics(
      child.descendant_card_count,
      input.viewport,
    );
    const diameter = metrics.diameter;
    const radius = diameter / 2;
    const compactDimension = Math.min(
      input.viewport.height,
      input.viewport.width,
    );
    const baseRadius = compactDimension * 0.24;
    const radiusStep = compactDimension * 0.18;
    const maximumRadius = compactDimension * 0.52;
    const targetRadius =
      index === 0
        ? 0
        : Math.min(baseRadius + Math.sqrt(index) * radiusStep, maximumRadius);
    const position = positionOnRing({
      center: input.center,
      index,
      nodeRadius: radius,
      targetRadius,
      viewport: input.viewport,
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
        .radius(
          (node) =>
            node.radius + lerp(8, 16, viewportWidthFactor(input.viewport)),
        )
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
    nodes: nodes.map((node) => {
      const metrics = buildBranchBubbleMetrics(
        node.child.descendant_card_count,
        input.viewport,
      );
      const center = clampCenterPosition({
        center: input.center,
        node,
        viewport: input.viewport,
      });

      return {
        data: {
          depth: node.child.depth,
          label: node.child.name,
          scope: "branch",
          targetNodeId:
            node.child.taxonomy_node_id ??
            (typeof node.child.id === "number" ? node.child.id : null),
          targetRoutePath: node.child.route_path,
          tooltip: `${node.child.name} · ${node.child.descendant_card_count} cards`,
        },
        id: node.id,
        position: {
          x: center.x - node.radius,
          y: center.y - node.radius,
        },
        style: {
          "--taxonomy-bubble-label-font-size": `${metrics.labelFontSize}px`,
          "--taxonomy-bubble-label-line-height": `${metrics.labelLineHeight}px`,
          "--taxonomy-bubble-label-width": `${metrics.labelMaxWidth}px`,
          borderRadius: `${node.diameter}px`,
          height: node.diameter,
          width: node.diameter,
        },
        type: "bubble" as const,
      };
    }),
  };
}
