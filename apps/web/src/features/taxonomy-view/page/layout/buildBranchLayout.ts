// abstract: Deterministic placeholder branch layout helper for weighted taxonomy bubbles.
// out_of_scope: Final force-simulation tuning and React Flow page orchestration.

import type {
  BranchLayoutInput,
  BranchLayoutResult,
  LayoutPoint,
} from "./taxonomyLayoutTypes";

export function bubbleDiameterFromDescendantCount(
  descendantCardCount: number,
): number {
  const scaled = 44 + Math.log(Math.max(descendantCardCount, 1) + 1) * 28;
  return Math.max(44, Math.min(Math.round(scaled), 120));
}

function positionOnRing(options: {
  readonly center: LayoutPoint;
  readonly index: number;
  readonly items: number;
}): LayoutPoint {
  const angle = ((2 * Math.PI) / Math.max(options.items, 1)) * options.index;
  const radius = 180 + options.index * 12;

  return {
    x: options.center.x + Math.cos(angle) * radius,
    y: options.center.y + Math.sin(angle) * radius,
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

  return {
    nodes: sortedChildren.map((child, index) => {
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
        id: `taxonomy-${child.id}`,
        position: positionOnRing({
          center: input.center,
          index,
          items: sortedChildren.length,
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
