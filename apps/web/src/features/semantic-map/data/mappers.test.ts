// abstract: Behavior tests for semantic-map manifest mapping.
// out_of_scope: Network requests and React rendering flows.

import type { components } from "@knowledge/contracts/generated/types";
import { describe, expect, it } from "vitest";

import { mapManifestToViewModel } from "./mappers";

function makeManifestFixture(): components["schemas"]["SemanticMapManifestResponse"] {
  return {
    built_at: "2026-04-03T13:45:00Z",
    coordinate_system: {
      axis_direction: "x-right-y-up",
      bounds_format: "min_x_min_y_max_x_max_y",
      kind: "cartesian2d",
    },
    default_semantic_level: 0,
    default_view: {
      target: [500, 500],
      zoom: 0,
    },
    max_zoom: 6,
    schema_version: "20260403_134500_000123",
    semantic_levels: [
      {
        child_content_role: "themes",
        display_name: "Domains",
        level: 0,
        max_zoom: 1,
        min_zoom: 0,
        region_role: "domain",
        stable_id: "domains",
      },
      {
        child_content_role: "topics",
        display_name: "Themes",
        level: 1,
        max_zoom: 3,
        min_zoom: 2,
        region_role: "theme",
        stable_id: "themes",
      },
    ],
    tile_size: 256,
    version: "20260403_134500_000123",
    world_bounds: [0, 0, 1000, 1000],
  };
}

describe("mapManifestToViewModel", () => {
  it("maps generated manifest data to the internal view model", () => {
    const result = mapManifestToViewModel(makeManifestFixture());

    expect(result.defaultSemanticLevel).toBe(0);
    expect(result.version).toBe("20260403_134500_000123");
    expect(result.levels).toHaveLength(2);
    expect(result.levels[0]?.stableId).toBe("domains");
  });
});
