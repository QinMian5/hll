// abstract: Contract tests for taxonomy branch and leaf layout helpers.
// out_of_scope: React Flow component mounting and browser-level visual fidelity.

import { describe, expect, it } from "vitest";

import {
  bubbleDiameterFromDescendantCount,
  buildBranchLayout,
} from "./buildBranchLayout";
import { buildLeafLayout } from "./buildLeafLayout";

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

function circlesOverlap(
  left: {
    readonly position: { readonly x: number; readonly y: number };
    readonly style: { readonly width: number };
  },
  right: {
    readonly position: { readonly x: number; readonly y: number };
    readonly style: { readonly width: number };
  },
) {
  const distance = Math.hypot(
    left.position.x - right.position.x,
    left.position.y - right.position.y,
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
  it("uses the configured logarithmic bubble sizing for branch nodes", () => {
    expect(bubbleDiameterFromDescendantCount(1)).toBe(100);
    expect(bubbleDiameterFromDescendantCount(10)).toBe(146);
    expect(bubbleDiameterFromDescendantCount(100)).toBe(192);
  });

  it("returns weighted bubbles with deterministic ids and finite positions", () => {
    const result = buildBranchLayout({
      center: { x: 700, y: 450 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 30, id: 2, name: "Culture" },
      ],
      viewport: { height: 900, width: 1404 },
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
      center: { x: 700, y: 450 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 30, id: 2, name: "Culture" },
      ],
      viewport: { height: 900, width: 1404 },
    });
    const second = buildBranchLayout({
      center: { x: 700, y: 450 },
      children: [
        { depth: 0, descendant_card_count: 300, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 30, id: 2, name: "Culture" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    expect(second.nodes.map((node) => node.id)).toEqual(
      first.nodes.map((node) => node.id),
    );
    expect(second.nodes.map((node) => roundPosition(node.position))).toEqual(
      first.nodes.map((node) => roundPosition(node.position)),
    );
  });

  it("prefers heavier bubbles near the center zone", () => {
    const center = { x: 702, y: 450 };
    const result = buildBranchLayout({
      center,
      children: [
        { depth: 0, descendant_card_count: 500, id: 1, name: "Science" },
        { depth: 0, descendant_card_count: 5, id: 2, name: "Culture" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    const heavy = result.nodes.find((node) => node.id === "taxonomy-1");
    const light = result.nodes.find((node) => node.id === "taxonomy-2");
    const heavyNode = expectNodePosition(heavy);
    const lightNode = expectNodePosition(light);

    expect(distanceFromCenter(heavyNode.position, center)).toBeLessThan(
      distanceFromCenter(lightNode.position, center),
    );
  });

  it("settles dense bubble sets without overlap", () => {
    const result = buildBranchLayout({
      center: { x: 702, y: 450 },
      children: Array.from({ length: 12 }, (_, index) => ({
        depth: 0,
        descendant_card_count: 400 - index,
        id: index + 1,
        name: `Node ${index + 1}`,
      })),
      viewport: { height: 900, width: 1404 },
    });

    const hasOverlap = result.nodes.some((node, index) =>
      result.nodes
        .slice(index + 1)
        .some((otherNode) => circlesOverlap(node, otherNode)),
    );

    expect(hasOverlap).toBe(false);
  });
});

describe("leaf layout contracts", () => {
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

  it("upgrades only visible hydrated node ids into bubble mode", () => {
    const result = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [[10, 11, 0.8]],
      hydratedNodeDetailsById: {
        10: {
          content: "Inner content",
          id: 10,
          scope: "inner",
          title: "Inner node",
        },
      },
      nodes: [
        { id: 10, scope: "inner" },
        { id: 11, scope: "outer" },
      ],
      viewport: { height: 900, width: 1404 },
      visibleBubbleNodeIds: [10],
    });

    const innerNode = result.nodes.find((node) => node.data.graphNodeId === 10);
    const outerNode = result.nodes.find((node) => node.data.graphNodeId === 11);

    expect(innerNode?.data.renderMode).toBe("bubble");
    expect(innerNode?.data.label).toBe("Inner node");
    expect(innerNode?.data.content).toBe("Inner content");
    expect(outerNode?.data.renderMode).toBe("point");
    expect(outerNode?.data.label).toBe("");
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

    const hub = result.nodes.find((node) => node.id === "card-50");
    const otherNodes = result.nodes.filter((node) => node.id !== "card-50");
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
