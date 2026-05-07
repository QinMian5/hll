// abstract: Contract tests for persistent leaf scene-model derivation helpers.
// out_of_scope: deck.gl layer wiring and React component rendering behavior.

import { describe, expect, it } from "vitest";

import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";
import {
  buildLeafSceneModelBase,
  buildLeafTitleLabelNodes,
  type LeafTitleTextMeasurer,
  selectLeafTitleNodeIdsByPriority,
  selectLeafTitleNodeIdsByScreenCollision,
} from "./useLeafSceneModel";

function makeCharacterWidthMeasurer(
  characterWidth: number,
): LeafTitleTextMeasurer {
  return {
    measureText: (text: string) => {
      const width = Array.from(text).length * characterWidth;

      return {
        actualBoundingBoxAscent: 16,
        actualBoundingBoxDescent: 4,
        actualBoundingBoxLeft: 0,
        actualBoundingBoxRight: width,
        width,
      };
    },
  };
}

function makeLayoutNodes(): readonly TaxonomyLayoutNode[] {
  return [
    {
      data: {
        depth: 0,
        graphNodeId: 10,
        label: "",
        renderMode: "point",
        scope: "inner",
        targetNodeId: null,
        tooltip: "",
      },
      id: "leaf-10",
      position: { x: 100, y: 100 },
      style: { borderRadius: "10px", height: 10, width: 10 },
      type: "bubble",
    },
    {
      data: {
        depth: 0,
        graphNodeId: 11,
        label: "",
        renderMode: "point",
        scope: "outer",
        targetNodeId: null,
        tooltip: "",
      },
      id: "leaf-11",
      position: { x: 200, y: 100 },
      style: { borderRadius: "10px", height: 10, width: 10 },
      type: "bubble",
    },
    {
      data: {
        depth: 0,
        graphNodeId: 12,
        label: "",
        renderMode: "point",
        scope: "outer",
        targetNodeId: null,
        tooltip: "",
      },
      id: "leaf-12",
      position: { x: 300, y: 100 },
      style: { borderRadius: "10px", height: 10, width: 10 },
      type: "bubble",
    },
  ];
}

describe("buildLeafSceneModelBase", () => {
  it("precomputes edge and focus subsets for hovered-node highlighting", () => {
    const scene = buildLeafSceneModelBase({
      edges: [
        [10, 11, 0.8],
        [11, 12, 0.7],
      ],
      layoutNodes: makeLayoutNodes(),
    });

    expect(
      scene.highlightEdgesByNodeId.get(11)?.map((edge) => edge.id),
    ).toEqual(["10:11", "11:12"]);
    expect(
      scene.highlightEdgesByNodeId.get(10)?.map((edge) => edge.id),
    ).toEqual(["10:11"]);
    const focusNodeIds = scene.focusNodeIdsByNodeId.get(11);

    expect(focusNodeIds).toBeDefined();
    expect([...(focusNodeIds as ReadonlySet<number>)]).toEqual([11, 10, 12]);
  });

  it("precomputes empty edge and self-focus entries for isolated point nodes", () => {
    const scene = buildLeafSceneModelBase({
      edges: [[10, 11, 0.8]],
      layoutNodes: makeLayoutNodes(),
    });

    const focusNodeIds = scene.focusNodeIdsByNodeId.get(12);

    expect(scene.highlightEdgesByNodeId.get(12)).toEqual([]);
    expect(focusNodeIds).toBeDefined();
    expect([...(focusNodeIds as ReadonlySet<number>)]).toEqual([12]);
  });
});

describe("buildLeafTitleLabelNodes", () => {
  it("keeps title labels display-only and ordered by visible node ids", () => {
    const scene = buildLeafSceneModelBase({
      edges: [[10, 11, 0.8]],
      layoutNodes: makeLayoutNodes(),
    });

    const labels = buildLeafTitleLabelNodes({
      pointNodes: scene.pointNodes,
      titlesByNodeId: {
        10: "Inner title",
        11: "Outer title",
      },
      visibleNodeIds: [11, 10, 12],
    });

    expect(labels.map((label) => [label.graphNodeId, label.title])).toEqual([
      [11, "Outer title"],
      [10, "Inner title"],
    ]);
    expect(labels[0]?.position).toEqual(scene.pointNodes[1]?.position);
  });
});

describe("selectLeafTitleNodeIdsByPriority", () => {
  it("keeps active nodes first, then higher-degree nodes", () => {
    const selected = selectLeafTitleNodeIdsByPriority({
      maxNodeCount: 3,
      neighborNodeIdsByNodeId: new Map([
        [10, new Set([11])],
        [11, new Set([10, 12, 13])],
        [12, new Set([11, 13])],
        [13, new Set()],
      ]),
      priorityNodeIds: [13],
      visibleNodeIds: [10, 11, 12, 13],
    });

    expect(selected).toEqual([13, 11, 12]);
  });
});

describe("selectLeafTitleNodeIdsByScreenCollision", () => {
  it("keeps the higher-degree title when two labels collide on screen", () => {
    const selected = selectLeafTitleNodeIdsByScreenCollision({
      canvas: { height: 240, width: 400 },
      neighborNodeIdsByNodeId: new Map([
        [10, new Set([12])],
        [11, new Set([12, 13, 14])],
        [12, new Set()],
      ]),
      pointNodes: [
        {
          graphNodeId: 10,
          id: "leaf-10",
          position: { x: 0, y: 0 },
          radius: 3,
          scope: "inner",
        },
        {
          graphNodeId: 11,
          id: "leaf-11",
          position: { x: 0, y: 0 },
          radius: 3,
          scope: "inner",
        },
        {
          graphNodeId: 12,
          id: "leaf-12",
          position: { x: 160, y: 0 },
          radius: 3,
          scope: "outer",
        },
      ],
      priorityNodeIds: [],
      titlesByNodeId: {
        10: "Low degree",
        11: "High degree",
        12: "Far title",
      },
      textMeasurer: makeCharacterWidthMeasurer(10),
      viewport: { target: [0, 0, 0], zoom: 0 },
      visibleNodeIds: [10, 11, 12],
    });

    expect(selected).toEqual([11, 12]);
  });

  it("uses tight measured text bounds instead of padding short labels", () => {
    const selected = selectLeafTitleNodeIdsByScreenCollision({
      canvas: { height: 240, width: 400 },
      neighborNodeIdsByNodeId: new Map(),
      pointNodes: [
        {
          graphNodeId: 1,
          id: "leaf-1",
          position: { x: -20, y: 0 },
          radius: 3,
          scope: "inner",
        },
        {
          graphNodeId: 2,
          id: "leaf-2",
          position: { x: 20, y: 0 },
          radius: 3,
          scope: "inner",
        },
      ],
      priorityNodeIds: [],
      textMeasurer: makeCharacterWidthMeasurer(8),
      titlesByNodeId: {
        1: "A",
        2: "B",
      },
      viewport: { target: [0, 0, 0], zoom: 0 },
      visibleNodeIds: [1, 2],
    });

    expect(selected).toEqual([1, 2]);
  });

  it("uses measured wrapping height when filtering lower-priority titles", () => {
    const selected = selectLeafTitleNodeIdsByScreenCollision({
      canvas: { height: 320, width: 800 },
      neighborNodeIdsByNodeId: new Map([
        [1, new Set([3, 4, 5])],
        [2, new Set()],
      ]),
      pointNodes: [
        {
          graphNodeId: 1,
          id: "leaf-1",
          position: { x: 0, y: 0 },
          radius: 3,
          scope: "inner",
        },
        {
          graphNodeId: 2,
          id: "leaf-2",
          position: { x: 100, y: 40 },
          radius: 3,
          scope: "inner",
        },
      ],
      priorityNodeIds: [],
      textMeasurer: makeCharacterWidthMeasurer(100),
      titlesByNodeId: {
        1: "aaaaa",
        2: "b",
      },
      viewport: { target: [0, 0, 0], zoom: 0 },
      visibleNodeIds: [1, 2],
    });

    expect(selected).toEqual([1]);
  });

  it("allows more labels as zoom spreads node anchors farther apart", () => {
    const pointNodes = Array.from({ length: 8 }, (_, index) => ({
      graphNodeId: index + 1,
      id: `leaf-${index + 1}`,
      position: { x: index * 16 - 56, y: 0 },
      radius: 3,
      scope: "inner" as const,
    }));
    const titlesByNodeId = Object.fromEntries(
      pointNodes.map((pointNode) => [pointNode.graphNodeId, "Heat title"]),
    );

    const lowZoom = selectLeafTitleNodeIdsByScreenCollision({
      canvas: { height: 240, width: 400 },
      neighborNodeIdsByNodeId: new Map(),
      pointNodes,
      priorityNodeIds: [],
      textMeasurer: makeCharacterWidthMeasurer(10),
      titlesByNodeId,
      viewport: { target: [0, 0, 0], zoom: 0 },
      visibleNodeIds: pointNodes.map((pointNode) => pointNode.graphNodeId),
    });
    const highZoom = selectLeafTitleNodeIdsByScreenCollision({
      canvas: { height: 240, width: 400 },
      neighborNodeIdsByNodeId: new Map(),
      pointNodes,
      priorityNodeIds: [],
      textMeasurer: makeCharacterWidthMeasurer(10),
      titlesByNodeId,
      viewport: { target: [0, 0, 0], zoom: 2 },
      visibleNodeIds: pointNodes.map((pointNode) => pointNode.graphNodeId),
    });

    expect(lowZoom.length).toBeLessThan(highZoom.length);
  });
});
