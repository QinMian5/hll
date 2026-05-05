// abstract: Unit tests for taxonomy leaf backend-layout render adaptation.
// out_of_scope: deck.gl layer construction and network query behavior.

import { describe, expect, it } from "vitest";

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../data/taxonomyViewQueries";
import { buildRenderableLeafLayout } from "./leafLayoutAdapter";

describe("buildRenderableLeafLayout", () => {
  it("returns an empty render layout while the slice is missing", () => {
    expect(buildRenderableLeafLayout(undefined)).toEqual({
      edges: [],
      nodes: [],
    });
  });

  it("converts backend card-scope points into production render nodes", () => {
    const layoutSlice: TaxonomyCardScopeLayoutSliceResponse = {
      edges: [[10, 11, 0.8]],
      layout_status: "ready",
      layout_version: "taxonomy-card-scope-layout-v2",
      nodes: [
        {
          id: 10,
          scope: "inner",
          x: 42,
          y: 58,
        },
      ],
      requested_bounds: {
        max_x: 100,
        max_y: 100,
        min_x: 0,
        min_y: 0,
      },
      route_path: "layout-lab/obsidian-sample",
      scope_kind: "taxonomy_node",
    };

    expect(buildRenderableLeafLayout(layoutSlice)).toEqual({
      edges: layoutSlice.edges,
      nodes: [
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
          position: {
            x: 34,
            y: 50,
          },
          style: {
            borderRadius: "16px",
            height: 16,
            width: 16,
          },
          type: "bubble",
        },
      ],
    });
  });
});
