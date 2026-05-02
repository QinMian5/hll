// abstract: Expanded-world branch layout helper for fixed-size weighted taxonomy bubbles.
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
  LayoutBounds,
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

const BRANCH_BOUNDS_MIN_PADDING = 24;
const BRANCH_INITIAL_VIEWPORT_DESKTOP_PADDING = 32;
const BRANCH_INITIAL_VIEWPORT_MOBILE_PADDING = 20;

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

function compareBranchChildIds(
  left: BranchLayoutInput["children"][number]["id"],
  right: BranchLayoutInput["children"][number]["id"],
) {
  if (typeof left === "number" && typeof right === "number") {
    return left - right;
  }

  return String(left).localeCompare(String(right));
}

function branchRingGap(viewport: LayoutViewport) {
  return lerp(28, 44, viewportWidthFactor(viewport));
}

function branchHaloPadding(diameter: number) {
  return Math.max(BRANCH_BOUNDS_MIN_PADDING, diameter * 0.18 + 14);
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

function ringSlotForIndex(index: number) {
  if (index === 0) {
    return {
      capacity: 1,
      ring: 0,
      slot: 0,
    };
  }

  let remaining = index - 1;
  let ring = 1;

  while (true) {
    const capacity = ring * 6;

    if (remaining < capacity) {
      return {
        capacity,
        ring,
        slot: remaining,
      };
    }

    remaining -= capacity;
    ring += 1;
  }
}

function positionOnRing(options: {
  readonly center: LayoutPoint;
  readonly capacity: number;
  readonly ring: number;
  readonly slot: number;
  readonly targetRadius: number;
}): LayoutPoint {
  if (options.ring === 0) {
    return options.center;
  }

  const angleStep = (Math.PI * 2) / options.capacity;
  const ringOffset = options.ring % 2 === 0 ? angleStep / 2 : 0;
  const angle = -Math.PI / 2 + ringOffset + options.slot * angleStep;

  return {
    x: options.center.x + Math.cos(angle) * options.targetRadius,
    y: options.center.y + Math.sin(angle) * options.targetRadius,
  };
}

function resolveBranchOverlaps(options: {
  readonly nodes: BranchSimulationNode[];
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
        moved = true;
      }
    }

    if (!moved) {
      break;
    }
  }
}

function branchLayoutBounds(
  nodes: readonly {
    readonly position: LayoutPoint;
    readonly style: { readonly height: number; readonly width: number };
  }[],
  center: LayoutPoint,
): LayoutBounds {
  if (nodes.length === 0) {
    return {
      maxX: center.x,
      maxY: center.y,
      minX: center.x,
      minY: center.y,
    };
  }

  return nodes.reduce<LayoutBounds>(
    (bounds, node) => {
      const haloPadding = branchHaloPadding(node.style.width);

      return {
        maxX: Math.max(
          bounds.maxX,
          node.position.x + node.style.width + haloPadding,
        ),
        maxY: Math.max(
          bounds.maxY,
          node.position.y + node.style.height + haloPadding,
        ),
        minX: Math.min(bounds.minX, node.position.x - haloPadding),
        minY: Math.min(bounds.minY, node.position.y - haloPadding),
      };
    },
    {
      maxX: Number.NEGATIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY,
      minX: Number.POSITIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
    },
  );
}

function branchInitialViewportPadding(viewport: LayoutViewport) {
  return viewport.width < 640
    ? BRANCH_INITIAL_VIEWPORT_MOBILE_PADDING
    : BRANCH_INITIAL_VIEWPORT_DESKTOP_PADDING;
}

function branchInitialViewport(bounds: LayoutBounds, viewport: LayoutViewport) {
  const boundsWidth = bounds.maxX - bounds.minX;
  const boundsHeight = bounds.maxY - bounds.minY;

  if (boundsWidth <= 0 || boundsHeight <= 0) {
    return {
      x: 0,
      y: 0,
      zoom: 1,
    };
  }

  const padding = branchInitialViewportPadding(viewport);
  const availableWidth = Math.max(1, viewport.width - padding * 2);
  const availableHeight = Math.max(1, viewport.height - padding * 2);
  const zoom = Math.min(
    1,
    availableWidth / boundsWidth,
    availableHeight / boundsHeight,
  );

  return {
    x: (viewport.width - boundsWidth * zoom) / 2 - bounds.minX * zoom,
    y: (viewport.height - boundsHeight * zoom) / 2 - bounds.minY * zoom,
    zoom,
  };
}

export function buildBranchLayout(
  input: BranchLayoutInput,
): BranchLayoutResult {
  const sortedChildren = [...input.children].sort(
    (left, right) =>
      right.descendant_card_count - left.descendant_card_count ||
      compareBranchChildIds(left.id, right.id),
  );
  const maximumDiameter = Math.max(
    ...sortedChildren
      .map((child) =>
        buildBranchBubbleMetrics(child.descendant_card_count, input.viewport),
      )
      .map((metrics) => metrics.diameter),
    0,
  );
  const centerRadius =
    sortedChildren.length > 0
      ? buildBranchBubbleMetrics(
          sortedChildren[0].descendant_card_count,
          input.viewport,
        ).diameter / 2
      : 0;
  const ringGap = branchRingGap(input.viewport);
  const ringStep = maximumDiameter + ringGap;

  const nodes: BranchSimulationNode[] = sortedChildren.map((child, index) => {
    const metrics = buildBranchBubbleMetrics(
      child.descendant_card_count,
      input.viewport,
    );
    const diameter = metrics.diameter;
    const radius = diameter / 2;
    const ringSlot = ringSlotForIndex(index);
    const targetRadius =
      ringSlot.ring === 0
        ? 0
        : centerRadius +
          maximumDiameter / 2 +
          ringGap +
          (ringSlot.ring - 1) * ringStep;
    const position = positionOnRing({
      capacity: ringSlot.capacity,
      center: input.center,
      ring: ringSlot.ring,
      slot: ringSlot.slot,
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
    nodes,
  });

  const layoutNodes = nodes.map((node) => {
    const metrics = buildBranchBubbleMetrics(
      node.child.descendant_card_count,
      input.viewport,
    );

    return {
      data: {
        depth: node.child.depth,
        label: node.child.name,
        scope: "branch" as const,
        targetNodeId:
          node.child.taxonomy_node_id ??
          (typeof node.child.id === "number" ? node.child.id : null),
        targetRoutePath: node.child.route_path,
        tooltip: `${node.child.name} · ${node.child.descendant_card_count} cards`,
      },
      id: node.id,
      position: {
        x: node.x - node.radius,
        y: node.y - node.radius,
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
  });
  const bounds = branchLayoutBounds(layoutNodes, input.center);

  return {
    bounds,
    initialViewport: branchInitialViewport(bounds, input.viewport),
    nodes: layoutNodes,
  };
}
