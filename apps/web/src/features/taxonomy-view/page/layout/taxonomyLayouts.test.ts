// abstract: Contract tests for taxonomy branch layout helpers.
// out_of_scope: React Flow component mounting and browser-level visual fidelity.

import { describe, expect, it } from "vitest";

import {
  BRANCH_DESKTOP_REFERENCE_VIEWPORT,
  BRANCH_MOBILE_REFERENCE_VIEWPORT,
  bubbleDiameterFromDescendantCount,
  buildBranchBubbleMetrics,
  buildBranchLayout,
} from "./buildBranchLayout";

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
        {
          depth: 0,
          descendant_card_count: 300,
          id: 1,
          name: "Science",
          route_path: "science",
        },
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
        {
          depth: 0,
          descendant_card_count: 300,
          id: 1,
          name: "Science",
          route_path: "science",
        },
        {
          depth: 0,
          descendant_card_count: 30,
          id: 2,
          name: "Culture",
          route_path: "culture",
        },
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
        {
          depth: 0,
          descendant_card_count: 300,
          id: 1,
          name: "Science",
          route_path: "science",
        },
        {
          depth: 0,
          descendant_card_count: 30,
          id: 2,
          name: "Culture",
          route_path: "culture",
        },
      ],
      viewport: BRANCH_DESKTOP_REFERENCE_VIEWPORT,
    });
    const second = buildBranchLayout({
      center: { x: 560, y: 512 },
      children: [
        {
          depth: 0,
          descendant_card_count: 300,
          id: 1,
          name: "Science",
          route_path: "science",
        },
        {
          depth: 0,
          descendant_card_count: 30,
          id: 2,
          name: "Culture",
          route_path: "culture",
        },
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
        {
          depth: 0,
          descendant_card_count: 500,
          id: 1,
          name: "Science",
          route_path: "science",
        },
        {
          depth: 0,
          descendant_card_count: 5,
          id: 2,
          name: "Culture",
          route_path: "culture",
        },
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
        route_path: `node-${index + 1}`,
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
        route_path: `node-${index + 1}`,
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
