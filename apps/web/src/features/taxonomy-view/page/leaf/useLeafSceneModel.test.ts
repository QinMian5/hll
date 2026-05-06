// abstract: Contract tests for persistent leaf scene-model derivation helpers.
// out_of_scope: deck.gl layer wiring and React component rendering behavior.

import { describe, expect, it } from "vitest";

import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";
import {
  buildLeafSceneModelBase,
  buildLeafTitleLabelNodes,
  selectLeafTitleNodeIdsByPriority,
} from "./useLeafSceneModel";

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
    expect([
      ...((scene.focusNodeIdsByNodeId.get(11) as ReadonlySet<number>) ??
        new Set()),
    ]).toEqual([11, 10, 12]);
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
