// abstract: Contract tests for deck.gl leaf viewport bounds and hydration selection helpers.
// out_of_scope: React component mounting and deck.gl controller behavior.

import { describe, expect, it } from "vitest";

import { buildLeafLayout } from "../layout/buildLeafLayout";
import { LEAF_POINT_TITLE_ACTIVATION_ZOOM } from "./leafRendererConfig";
import {
  buildLeafViewportState,
  selectLeafHydrationNodeIds,
} from "./useLeafViewportController";

describe("leaf viewport controller helpers", () => {
  it("keeps point-title mode inactive below the activation zoom", () => {
    const state = buildLeafViewportState({
      canvas: { height: 900, width: 1404 },
      overscan: 160,
      viewport: {
        target: [702, 450, 0],
        zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM - 0.1,
      },
    });

    expect(state.isPointTitleModeActive).toBe(false);
  });

  it("computes world and overscan bounds from orthographic viewport state", () => {
    const state = buildLeafViewportState({
      canvas: { height: 900, width: 1404 },
      overscan: 160,
      viewport: { target: [702, 450, 0], zoom: 1 },
    });

    expect(state.isPointTitleModeActive).toBe(true);
    expect(state.bounds.left).toBeCloseTo(351);
    expect(state.bounds.right).toBeCloseTo(1053);
    expect(state.overscanBounds.left).toBeLessThan(state.bounds.left);
    expect(state.overscanBounds.right).toBeGreaterThan(state.bounds.right);
  });

  it("selects only nodes intersecting the overscan bounds", () => {
    const layout = buildLeafLayout({
      center: { x: 700, y: 450 },
      edges: [[10, 11, 0.8]],
      nodes: [
        { id: 10, scope: "inner" },
        { id: 11, scope: "outer" },
      ],
      viewport: { height: 900, width: 1404 },
    });
    const centeredState = buildLeafViewportState({
      canvas: { height: 900, width: 1404 },
      overscan: 0,
      viewport: { target: [700, 450, 0], zoom: 1.5 },
    });
    const offscreenState = buildLeafViewportState({
      canvas: { height: 900, width: 1404 },
      overscan: 0,
      viewport: { target: [1200, 900, 0], zoom: 1.5 },
    });

    expect(
      selectLeafHydrationNodeIds(layout.nodes, centeredState.bounds),
    ).toEqual(expect.arrayContaining([10, 11]));
    expect(
      selectLeafHydrationNodeIds(layout.nodes, offscreenState.bounds),
    ).toHaveLength(0);
  });
});
