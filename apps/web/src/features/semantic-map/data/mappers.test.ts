// abstract: Behavior tests for semantic-map manifest mapping.
// out_of_scope: Network requests and React rendering flows.

import type { components } from "@knowledge/contracts/generated/types";
import { describe, expect, it } from "vitest";

import { mapManifestToViewModel, mapRegionTileToViewModel } from "./mappers";

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

describe("mapRegionTileToViewModel", () => {
  it("maps tile points into the internal point view model", () => {
    const result = mapRegionTileToViewModel({
      edges: [
        {
          id: "edge:42:7",
          source_node_id: 42,
          source_position: [512, 488],
          strength: 0.9,
          target_node_id: 7,
          target_position: [520, 500],
        },
      ],
      labels: [],
      points: [
        {
          id: "card:42",
          leaf_region_id: "taxonomy:9",
          node_id: 42,
          position: [512, 488],
          title: "Card Title",
        },
      ],
      regions: [],
      schema_version: "20260403_134500_000123",
      semantic_level: 3,
      stats: {
        edge_count: 1,
        label_count: 0,
        region_count: 0,
      },
      tile: {
        bounds_format: "min_x_min_y_max_x_max_y",
        tile_bounds: [0, 0, 1000, 1000],
        x: 0,
        y: 0,
        z: 0,
      },
      version: "20260403_134500_000123",
    });

    expect(result.points).toHaveLength(1);
    expect(result.points[0]?.nodeId).toBe(42);
    expect(result.points[0]?.title).toBe("Card Title");
    expect(result.points[0]?.leafRegionId).toBe("taxonomy:9");
    expect(result.edges[0]?.id).toBe("edge:42:7");
    expect(result.stats.edgeCount).toBe(1);
  });
});
