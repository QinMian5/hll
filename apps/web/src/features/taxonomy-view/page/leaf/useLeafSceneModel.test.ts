// abstract: Contract tests for persistent leaf scene-model derivation helpers.
// out_of_scope: deck.gl layer wiring and React component rendering behavior.

import { describe, expect, it } from "vitest";

import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";
import { buildLeafSceneModelBase } from "./useLeafSceneModel";

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
      id: "card-10",
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
      id: "card-11",
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
      id: "card-12",
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
