// abstract: Behavior tests for leaf zoom-control percentage and deck zoom mapping.
// out_of_scope: React zoom-control rendering and deck.gl viewport publication.

import { describe, expect, it } from "vitest";

import { LEAF_POINT_TITLE_ACTIVATION_ZOOM } from "./leafRendererConfig";
import {
  clampLeafZoomPercent,
  deckZoomToLeafZoomPercent,
  getNextLeafZoomSnap,
  getPreviousLeafZoomSnap,
  leafZoomPercentToDeckZoom,
  leafZoomPercentToTrackPosition,
  leafZoomTrackPositionToPercent,
  snapLeafZoomPercent,
} from "./leafZoomControl";

describe("leafZoomControl", () => {
  it("maps the point-title activation threshold to 100 percent", () => {
    expect(
      deckZoomToLeafZoomPercent(LEAF_POINT_TITLE_ACTIVATION_ZOOM),
    ).toBeCloseTo(100);
    expect(leafZoomPercentToDeckZoom(100)).toBeCloseTo(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM,
    );
  });

  it("maps each doubling stop to one deck zoom unit", () => {
    expect(leafZoomPercentToDeckZoom(25)).toBeCloseTo(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM - 2,
    );
    expect(leafZoomPercentToDeckZoom(50)).toBeCloseTo(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM - 1,
    );
    expect(leafZoomPercentToDeckZoom(200)).toBeCloseTo(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM + 1,
    );
    expect(leafZoomPercentToDeckZoom(400)).toBeCloseTo(
      LEAF_POINT_TITLE_ACTIVATION_ZOOM + 2,
    );
  });

  it("clamps percentages to the Figma zoom-control range", () => {
    expect(clampLeafZoomPercent(10)).toBe(25);
    expect(clampLeafZoomPercent(75)).toBe(75);
    expect(clampLeafZoomPercent(800)).toBe(400);
  });

  it("only snaps settled percentages inside the 5 percent track-radius", () => {
    expect(snapLeafZoomPercent(28.5)).toBe(25);
    expect(snapLeafZoomPercent(57)).toBe(50);
    expect(snapLeafZoomPercent(113)).toBe(100);
    expect(snapLeafZoomPercent(225)).toBe(200);

    expect(snapLeafZoomPercent(29)).toBeCloseTo(29);
    expect(snapLeafZoomPercent(75)).toBeCloseTo(75);
    expect(snapLeafZoomPercent(116)).toBeCloseTo(116);
    expect(snapLeafZoomPercent(150)).toBeCloseTo(150);
    expect(snapLeafZoomPercent(235)).toBeCloseTo(235);
  });

  it("keeps the old broad-snap examples outside the limited magnetic radius continuous", () => {
    expect(
      snapLeafZoomPercent(leafZoomTrackPositionToPercent(0.56)),
    ).toBeCloseTo(leafZoomTrackPositionToPercent(0.56));
  });

  it("uses one normalized track coordinate system for ticks and pointer positions", () => {
    expect(leafZoomPercentToTrackPosition(25)).toBeCloseTo(0);
    expect(leafZoomPercentToTrackPosition(50)).toBeCloseTo(0.25);
    expect(leafZoomPercentToTrackPosition(100)).toBeCloseTo(0.5);
    expect(leafZoomPercentToTrackPosition(200)).toBeCloseTo(0.75);
    expect(leafZoomPercentToTrackPosition(400)).toBeCloseTo(1);

    expect(leafZoomTrackPositionToPercent(0)).toBeCloseTo(25);
    expect(leafZoomTrackPositionToPercent(0.25)).toBeCloseTo(50);
    expect(leafZoomTrackPositionToPercent(0.5)).toBeCloseTo(100);
    expect(leafZoomTrackPositionToPercent(0.75)).toBeCloseTo(200);
    expect(leafZoomTrackPositionToPercent(1)).toBeCloseTo(400);
  });

  it("steps to adjacent configured zoom stops", () => {
    expect(getNextLeafZoomSnap(25)).toBe(50);
    expect(getNextLeafZoomSnap(75)).toBe(100);
    expect(getNextLeafZoomSnap(400)).toBe(400);

    expect(getPreviousLeafZoomSnap(400)).toBe(200);
    expect(getPreviousLeafZoomSnap(150)).toBe(100);
    expect(getPreviousLeafZoomSnap(25)).toBe(25);
  });
});
