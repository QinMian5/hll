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

describe("branch layout contracts", () => {
  it("uses logarithmic bubble sizing", () => {
    expect(bubbleDiameterFromDescendantCount(1)).toBeLessThan(
      bubbleDiameterFromDescendantCount(100),
    );
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
});

describe("leaf layout contracts", () => {
  it("returns title-first nodes and preserves supplied edges", () => {
    const result = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [
        { id: "e-1", source_node_id: 10, strength: 0.8, target_node_id: 11 },
      ],
      nodes: [
        {
          content: "Inner content",
          id: 10,
          scope: "inner",
          title: "Inner node",
        },
        {
          content: "Outer content",
          id: 11,
          scope: "outer",
          title: "Outer node",
        },
      ],
      viewport: { height: 900, width: 1404 },
    });

    expect(result.nodes).toHaveLength(2);
    expect(result.edges).toHaveLength(1);
    expect(result.nodes[0]?.data.label).toBe("Inner node");
    expect(result.nodes[0]?.data.content).toBe("Inner content");
  });

  it("keeps rounded positions stable for identical graph input", () => {
    const input = {
      center: { x: 700, y: 450 },
      edges: [
        { id: "e-1", source_node_id: 10, strength: 0.8, target_node_id: 11 },
        { id: "e-2", source_node_id: 11, strength: 0.5, target_node_id: 12 },
      ],
      nodes: [
        {
          content: "Inner content",
          id: 10,
          scope: "inner" as const,
          title: "Inner node",
        },
        {
          content: "Outer content",
          id: 11,
          scope: "outer" as const,
          title: "Outer node",
        },
        {
          content: "Third content",
          id: 12,
          scope: "outer" as const,
          title: "Third node",
        },
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
});
