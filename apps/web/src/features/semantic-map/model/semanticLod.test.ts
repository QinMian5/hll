// abstract: Behavior tests for semantic-map semantic-zoom level selection.
// out_of_scope: React rendering and deck.gl canvas integration.

import { describe, expect, it } from "vitest";

import type { SemanticMapLevelViewModel } from "../data/mappers";
import { getSemanticZoomState } from "./semanticLod";

const fixtureLevels: readonly SemanticMapLevelViewModel[] = [
  {
    childContentRole: "themes",
    displayName: "Domains",
    level: 0,
    maxZoom: 1,
    minZoom: 0,
    regionRole: "domain",
    stableId: "domains",
  },
  {
    childContentRole: "topics",
    displayName: "Themes",
    level: 1,
    maxZoom: 3,
    minZoom: 2,
    regionRole: "theme",
    stableId: "themes",
  },
];

describe("getSemanticZoomState", () => {
  it("selects the configured default semantic level for the initial zoom", () => {
    const result = getSemanticZoomState({
      defaultSemanticLevel: 0,
      levels: fixtureLevels,
      zoom: -4,
    });

    expect(result.baseLevel).toBe(0);
    expect(result.activeLevel.stableId).toBe("domains");
  });
});
