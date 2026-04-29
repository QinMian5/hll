// abstract: Contract tests for taxonomy branch and leaf layout helpers.
// out_of_scope: React Flow component mounting and browser-level visual fidelity.

import { describe, expect, it } from "vitest";

import {
  BRANCH_DESKTOP_REFERENCE_VIEWPORT,
  BRANCH_MOBILE_REFERENCE_VIEWPORT,
  bubbleDiameterFromDescendantCount,
  buildBranchBubbleMetrics,
  buildBranchLayout,
} from "./buildBranchLayout";
import {
  buildLeafLayout,
  LEAF_COLLISION_RADIUS,
  LEAF_POINT_DIAMETER,
  scalePointAroundCenter,
} from "./buildLeafLayout";

function roundPosition(position: { readonly x: number; readonly y: number }) {
  return {
    x: Math.round(position.x),
    y: Math.round(position.y),
  };
}

function distanceFromCenter(
  position: { readonly x: number; readonly y: number },
  center: { readonly x: number; readonly y: number },
) {
  return Math.hypot(position.x - center.x, position.y - center.y);
}

function nodeCenter(node: {
  readonly position: { readonly x: number; readonly y: number };
  readonly style: { readonly height: number; readonly width: number };
}) {
  return {
    x: node.position.x + node.style.width / 2,
    y: node.position.y + node.style.height / 2,
  };
}

function circlesOverlap(
  left: {
    readonly position: { readonly x: number; readonly y: number };
    readonly style: { readonly height: number; readonly width: number };
  },
  right: {
    readonly position: { readonly x: number; readonly y: number };
    readonly style: { readonly height: number; readonly width: number };
  },
) {
  const leftCenter = nodeCenter(left);
  const rightCenter = nodeCenter(right);
  const distance = Math.hypot(
    leftCenter.x - rightCenter.x,
    leftCenter.y - rightCenter.y,
  );
  return distance < left.style.width / 2 + right.style.width / 2;
}

function expectNodePosition<
  T extends { readonly position: { readonly x: number; readonly y: number } },
>(node: T | undefined) {
  expect(node).toBeDefined();
  return node as T;
}

describe("branch layout contracts", () => {
  it("uses Figma reference viewport metrics for branch bubbles", () => {
    expect(BRANCH_DESKTOP_REFERENCE_VIEWPORT).toEqual({
      height: 1024,
      width: 1120,
    });
    expect(BRANCH_MOBILE_REFERENCE_VIEWPORT).toEqual({
      height: 892,
      width: 440,
    });
    expect(bubbleDiameterFromDescendantCount(10)).toBe(146);
    expect(
      buildBranchBubbleMetrics(10, BRANCH_DESKTOP_REFERENCE_VIEWPORT).diameter,
    ).toBe(146);
    expect(
      buildBranchBubbleMetrics(10, BRANCH_MOBILE_REFERENCE_VIEWPORT).diameter,
    ).toBe(100);
    expect(
      buildBranchBubbleMetrics(1000, BRANCH_DESKTOP_REFERENCE_VIEWPORT)
        .diameter,
    ).toBeLessThanOrEqual(236);
    expect(
      buildBranchBubbleMetrics(1000, BRANCH_MOBILE_REFERENCE_VIEWPORT).diameter,
    ).toBeLessThanOrEqual(132);
  });

  it("emits label sizing variables for branch bubble nodes", () => {
    const result = buildBranchLayout({
      center: { x: 560, y: 512 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
      ],
      viewport: BRANCH_DESKTOP_REFERENCE_VIEWPORT,
    });

    const node = result.nodes[0];

    expect(node?.style["--taxonomy-bubble-label-width"]).toMatch(/px$/);
    expect(node?.style["--taxonomy-bubble-label-font-size"]).toMatch(/px$/);
    expect(node?.style["--taxonomy-bubble-label-line-height"]).toMatch(/px$/);
  });

  it("returns weighted bubbles with deterministic ids and finite positions", () => {
    const result = buildBranchLayout({
      center: { x: 560, y: 512 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 30, id: 2, name: "Culture" },
      ],
      viewport: BRANCH_DESKTOP_REFERENCE_VIEWPORT,
    });

    expect(result.nodes).toHaveLength(2);
    expect(result.nodes[0]?.id).toBe("taxonomy-1");
    expect(
      result.nodes.every(
        (node) =>
          Number.isFinite(node.position.x) && Number.isFinite(node.position.y),
      ),
    ).toBe(true);
  });

  it("keeps rounded positions stable for identical input", () => {
    const first = buildBranchLayout({
      center: { x: 560, y: 512 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 30, id: 2, name: "Culture" },
      ],
      viewport: BRANCH_DESKTOP_REFERENCE_VIEWPORT,
    });
    const second = buildBranchLayout({
      center: { x: 560, y: 512 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 30, id: 2, name: "Culture" },
      ],
      viewport: BRANCH_DESKTOP_REFERENCE_VIEWPORT,
    });

    expect(second.nodes.map((node) => node.id)).toEqual(
      first.nodes.map((node) => node.id),
    );
    expect(second.nodes.map((node) => roundPosition(node.position))).toEqual(
      first.nodes.map((node) => roundPosition(node.position)),
    );
  });

  it("prefers heavier bubbles near the center zone", () => {
    const center = { x: 560, y: 512 };
    const result = buildBranchLayout({
      center,
      children: [
        { depth: 0, descendant_card_count: 500, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 5, id: 2, name: "Culture" },
      ],
      viewport: BRANCH_DESKTOP_REFERENCE_VIEWPORT,
    });

    const heavy = result.nodes.find((node) => node.id === "taxonomy-1");
    const light = result.nodes.find((node) => node.id === "taxonomy-2");
    const heavyNode = expectNodePosition(heavy);
    const lightNode = expectNodePosition(light);

    expect(distanceFromCenter(nodeCenter(heavyNode), center)).toBeLessThan(
      distanceFromCenter(nodeCenter(lightNode), center),
    );
  });

  it("settles dense bubble sets without overlap", () => {
    const result = buildBranchLayout({
      center: { x: 560, y: 512 },
      children: Array.from({ length: 12 }, (_, index) => ({
        depth: 0,
        descendant_card_count: 400 - index,
        id: index + 1,
        name: `Node ${index + 1}`,
      })),
      viewport: BRANCH_DESKTOP_REFERENCE_VIEWPORT,
    });

    const hasOverlap = result.nodes.some((node, index) =>
      result.nodes
        .slice(index + 1)
        .some((otherNode) => circlesOverlap(node, otherNode)),
    );

    expect(hasOverlap).toBe(false);
  });

  it("keeps branch bubbles contained on the mobile Figma viewport", () => {
    const result = buildBranchLayout({
      center: { x: 220, y: 446 },
      children: Array.from({ length: 9 }, (_, index) => ({
        depth: 1,
        descendant_card_count: 300 - index * 20,
        id: index + 1,
        name: `Node ${index + 1}`,
      })),
      viewport: BRANCH_MOBILE_REFERENCE_VIEWPORT,
    });

    expect(result.nodes.every((node) => node.position.x >= 0)).toBe(true);
    expect(result.nodes.every((node) => node.position.y >= 0)).toBe(true);
    expect(
      result.nodes.every(
        (node) =>
          node.position.x + node.style.width <=
          BRANCH_MOBILE_REFERENCE_VIEWPORT.width,
      ),
    ).toBe(true);
    expect(
      result.nodes.every(
        (node) =>
          node.position.y + node.style.height <=
          BRANCH_MOBILE_REFERENCE_VIEWPORT.height,
      ),
    ).toBe(true);
    expect(result.nodes.every((node) => node.style.width <= 132)).toBe(true);
  });
});

describe("leaf layout contracts", () => {
  it("scales solved node centers outward from the shared layout center", () => {
    expect(
      scalePointAroundCenter({ x: 760, y: 500 }, { x: 700, y: 450 }, 2),
    ).toEqual({
      x: 820,
      y: 550,
    });
  });

  it("uses the configured fixed collision radius for leaf spacing", () => {
    expect(LEAF_COLLISION_RADIUS).toBe(25);
  });

  it("returns point-mode skeleton nodes and preserves supplied edges by default", () => {
    const result = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [[10, 11, 0.8]],
      nodes: [
        { id: 10, scope: "inner" },
        { id: 11, scope: "outer" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    expect(result.nodes).toHaveLength(2);
    expect(result.edges).toHaveLength(1);
    expect(result.nodes[0]?.data.renderMode).toBe("point");
    expect(result.nodes[0]?.data.label).toBe("");
    expect(result.nodes[0]?.data.content).toBeUndefined();
  });

  it("keeps all leaf nodes as uniform point geometry", () => {
    const result = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [[10, 11, 0.8]],
      nodes: [
        { id: 10, scope: "inner" },
        { id: 11, scope: "outer" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    expect(
      result.nodes.map((node) => ({
        height: node.style.height,
        mode: node.data.renderMode,
        scope: node.data.scope,
        width: node.style.width,
      })),
    ).toEqual([
      {
        height: LEAF_POINT_DIAMETER,
        mode: "point",
        scope: "inner",
        width: LEAF_POINT_DIAMETER,
      },
      {
        height: LEAF_POINT_DIAMETER,
        mode: "point",
        scope: "outer",
        width: LEAF_POINT_DIAMETER,
      },
    ]);
  });

  it("preserves locked node centers without changing point dimensions", () => {
    const skeleton = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [],
      nodes: [{ id: 10, scope: "inner" }],
      viewport: { height: 900, width: 1404 },
    });
    const skeletonNode = skeleton.nodes[0];
    const lockedCenter = {
      x: (skeletonNode?.position.x ?? 0) + (skeletonNode?.style.width ?? 0) / 2,
      y:
        (skeletonNode?.position.y ?? 0) + (skeletonNode?.style.height ?? 0) / 2,
    };

    const result = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [],
      lockedNodeCentersById: new Map([[10, lockedCenter]]),
      nodes: [{ id: 10, scope: "inner" }],
      viewport: { height: 900, width: 1404 },
    });

    const pointNode = result.nodes[0];

    expect(pointNode?.style.width).toBe(LEAF_POINT_DIAMETER);
    expect(pointNode?.style.height).toBe(LEAF_POINT_DIAMETER);
    expect(
      (pointNode?.position.x ?? 0) + (pointNode?.style.width ?? 0) / 2,
    ).toBeCloseTo(lockedCenter.x, 4);
    expect(
      (pointNode?.position.y ?? 0) + (pointNode?.style.height ?? 0) / 2,
    ).toBeCloseTo(lockedCenter.y, 4);
  });

  it("keeps rounded positions stable for identical graph input", () => {
    const input = {
      center: { x: 700, y: 450 },
      edges: [
        [10, 11, 0.8],
        [11, 12, 0.5],
      ] as const,
      nodes: [
        { id: 10, scope: "inner" as const },
        { id: 11, scope: "outer" as const },
        { id: 12, scope: "outer" as const },
      ],
      viewport: { height: 900, width: 1404 },
    };

    const first = buildLeafLayout(input);
    const second = buildLeafLayout(input);

    expect(second.nodes.map((node) => node.id)).toEqual(
      first.nodes.map((node) => node.id),
    );
    expect(second.nodes.map((node) => roundPosition(node.position))).toEqual(
      first.nodes.map((node) => roundPosition(node.position)),
    );
  });

  it("pulls highly connected hub nodes toward the center zone", () => {
    const center = { x: 700, y: 450 };
    const result = buildLeafLayout({
      center,
      edges: [
        [50, 10, 1],
        [50, 20, 1],
        [50, 30, 1],
        [50, 40, 1],
      ],
      nodes: [
        { id: 10, scope: "outer" },
        { id: 20, scope: "outer" },
        { id: 30, scope: "inner" },
        { id: 40, scope: "outer" },
        { id: 50, scope: "inner" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    const hub = result.nodes.find((node) => node.id === "leaf-50");
    const otherNodes = result.nodes.filter((node) => node.id !== "leaf-50");
    const hubNode = expectNodePosition(hub);
    const averageOtherDistance =
      otherNodes.reduce(
        (sum, node) => sum + distanceFromCenter(node.position, center),
        0,
      ) / otherNodes.length;

    expect(distanceFromCenter(hubNode.position, center)).toBeLessThan(
      averageOtherDistance,
    );
  });
});
