// abstract: Contract tests for mapping leaf layout output into deck.gl-ready scene primitives.
// out_of_scope: deck.gl layer instantiation and React component behavior.

import { describe, expect, it } from "vitest";

import { buildLeafLayout } from "../layout/buildLeafLayout";
import { buildLeafSceneModel } from "./useLeafSceneModel";

describe("leaf scene model shaping", () => {
  it("keeps all leaf nodes in the point layer when no cards are hydrated", () => {
    const layout = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [[10, 11, 0.8]],
      nodes: [
        { id: 10, scope: "inner" },
        { id: 11, scope: "outer" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    const scene = buildLeafSceneModel({
      edges: [[10, 11, 0.8]],
      layoutNodes: layout.nodes,
    });

    expect(scene.cardNodes).toHaveLength(0);
    expect(scene.pointNodes).toHaveLength(2);
    expect(scene.edges).toHaveLength(1);
  });

  it("promotes only hydrated visible nodes into card layer data", () => {
    const layout = buildLeafLayout({
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
      visibleCardNodeIds: [10],
    });

    const scene = buildLeafSceneModel({
      edges: [[10, 11, 0.8]],
      layoutNodes: layout.nodes,
    });

    expect(scene.cardNodes.map((node) => node.graphNodeId)).toEqual([10]);
    expect(scene.pointNodes.map((node) => node.graphNodeId)).toEqual([11]);
    expect(scene.cardNodes[0]?.label).toBe("Inner node");
  });

  it("anchors edge endpoints to the node centers", () => {
    const layout = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [[10, 11, 0.8]],
      nodes: [
        { id: 10, scope: "inner" },
        { id: 11, scope: "outer" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    const scene = buildLeafSceneModel({
      edges: [[10, 11, 0.8]],
      layoutNodes: layout.nodes,
    });

    expect(scene.edges[0]?.source).toEqual(scene.pointNodes[0]?.position);
    expect(scene.edges[0]?.target).toEqual(scene.pointNodes[1]?.position);
  });

  it("builds incident edge and neighbor indexes for hover focus state", () => {
    const layout = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [
        [10, 11, 0.8],
        [10, 12, 0.5],
      ],
      nodes: [
        { id: 10, scope: "inner" },
        { id: 11, scope: "outer" },
        { id: 12, scope: "outer" },
      ],
      viewport: { height: 900, width: 1404 },
    });

    const scene = buildLeafSceneModel({
      edges: [
        [10, 11, 0.8],
        [10, 12, 0.5],
      ],
      layoutNodes: layout.nodes,
    });

    expect([...(scene.edgeIdsByNodeId.get(10) ?? new Set()).values()]).toEqual(
      expect.arrayContaining(["10:11", "10:12"]),
    );
    expect([
      ...(scene.neighborNodeIdsByNodeId.get(10) ?? new Set()).values(),
    ]).toEqual(expect.arrayContaining([11, 12]));
  });
});
