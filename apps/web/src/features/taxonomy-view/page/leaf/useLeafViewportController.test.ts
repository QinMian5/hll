// abstract: Contract tests for deck.gl leaf viewport bounds and hydration selection helpers.
// out_of_scope: React component mounting and deck.gl controller behavior.

import { describe, expect, it } from "vitest";

import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";
import {
  LEAF_POINT_TITLE_ACTIVATION_ZOOM,
  LEAF_POINT_TITLE_FADE_END_ZOOM,
  LEAF_POINT_TITLE_FADE_START_ZOOM,
} from "./leafRendererConfig";
import {
  buildInitialLeafViewport,
  buildLeafViewportState,
  isLeafPointTitleHydrationActive,
  isLeafPointTitleModeActive,
  leafPointTitleOpacity,
  selectLeafHydrationNodeIds,
  snapLeafWorldBoundsToTile,
} from "./useLeafViewportController";

function makeLayoutPointNode(options: {
  readonly id: number;
  readonly scope: "inner" | "outer";
  readonly x: number;
  readonly y: number;
}): TaxonomyLayoutNode {
  return {
    data: {
      depth: 0,
      graphNodeId: options.id,
      label: "",
      renderMode: "point",
      scope: options.scope,
      targetNodeId: null,
      tooltip: "",
    },
    id: `leaf-${options.id}`,
    position: { x: options.x, y: options.y },
    style: {
      borderRadius: "8px",
      height: 8,
      width: 8,
    },
    type: "bubble",
  };
}

describe("leaf viewport controller helpers", () => {
  it("uses one inclusive zoom threshold for point-title mode", () => {
    expect(
      isLeafPointTitleModeActive(LEAF_POINT_TITLE_ACTIVATION_ZOOM - 0.001),
    ).toBe(false);
    expect(isLeafPointTitleModeActive(LEAF_POINT_TITLE_ACTIVATION_ZOOM)).toBe(
      true,
    );
    expect(
      isLeafPointTitleModeActive(LEAF_POINT_TITLE_ACTIVATION_ZOOM + 0.001),
    ).toBe(true);
  });

  it("hydrates titles across a lower fade-start threshold", () => {
    expect(
      isLeafPointTitleHydrationActive(LEAF_POINT_TITLE_FADE_START_ZOOM - 0.001),
    ).toBe(false);
    expect(
      isLeafPointTitleHydrationActive(LEAF_POINT_TITLE_FADE_START_ZOOM),
    ).toBe(true);
    expect(
      isLeafPointTitleHydrationActive(LEAF_POINT_TITLE_ACTIVATION_ZOOM - 0.001),
    ).toBe(true);
  });

  it("computes smooth title opacity across the fade zoom range", () => {
    const midpointZoom =
      (LEAF_POINT_TITLE_FADE_START_ZOOM + LEAF_POINT_TITLE_FADE_END_ZOOM) / 2;

    expect(
      leafPointTitleOpacity(LEAF_POINT_TITLE_FADE_START_ZOOM - 0.001),
    ).toBe(0);
    expect(leafPointTitleOpacity(LEAF_POINT_TITLE_FADE_START_ZOOM)).toBe(0);
    expect(leafPointTitleOpacity(midpointZoom)).toBeCloseTo(0.5);
    expect(leafPointTitleOpacity(LEAF_POINT_TITLE_FADE_END_ZOOM)).toBe(1);
    expect(leafPointTitleOpacity(LEAF_POINT_TITLE_FADE_END_ZOOM + 0.001)).toBe(
      1,
    );
  });

  it("computes world and overscan bounds from orthographic viewport state", () => {
    const state = buildLeafViewportState({
      canvas: { height: 900, width: 1404 },
      overscan: 160,
      viewport: { target: [702, 450, 0], zoom: 1 },
    });

    expect(state.bounds.left).toBeCloseTo(351);
    expect(state.bounds.right).toBeCloseTo(1053);
    expect(state.overscanBounds.left).toBeLessThan(state.bounds.left);
    expect(state.overscanBounds.right).toBeGreaterThan(state.bounds.right);
  });

  it("starts the initial leaf viewport just above the point-title threshold", () => {
    const compactViewport = buildInitialLeafViewport({
      canvas: { height: 800, width: 1200 },
      padding: 160,
      worldBounds: { bottom: 120, left: -200, right: 200, top: -120 },
    });
    const wideViewport = buildInitialLeafViewport({
      canvas: { height: 800, width: 1200 },
      padding: 160,
      worldBounds: { bottom: 500, left: -1400, right: 1400, top: -500 },
    });

    expect(compactViewport.target).toEqual([0, 0, 0]);
    expect(compactViewport.zoom).toBeGreaterThan(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM,
    );
    expect(compactViewport.zoom).toBeCloseTo(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM + 0.01,
    );
    expect(wideViewport.target).toEqual([0, 0, 0]);
    expect(wideViewport.zoom).toBeCloseTo(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM + 0.01,
    );
  });

  it("selects only nodes intersecting the overscan bounds", () => {
    const layoutNodes = [
      makeLayoutPointNode({ id: 10, scope: "inner", x: 696, y: 446 }),
      makeLayoutPointNode({ id: 11, scope: "outer", x: 736, y: 476 }),
    ];
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
      selectLeafHydrationNodeIds(layoutNodes, centeredState.bounds),
    ).toEqual(expect.arrayContaining([10, 11]));
    expect(
      selectLeafHydrationNodeIds(layoutNodes, offscreenState.bounds),
    ).toHaveLength(0);
  });

  it("snaps nearby world bounds to stable layout tiles", () => {
    const first = snapLeafWorldBoundsToTile(
      { bottom: 610, left: -862, right: 862, top: -610 },
      1024,
    );
    const second = snapLeafWorldBoundsToTile(
      { bottom: 624, left: -840, right: 884, top: -588 },
      1024,
    );

    expect(first).toEqual({
      bottom: 1024,
      left: -1024,
      right: 1024,
      top: -1024,
    });
    expect(second).toEqual(first);
  });
});
