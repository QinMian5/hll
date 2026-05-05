// abstract: Unit tests for the standalone taxonomy layout lab preview.
// out_of_scope: Real WebGL rendering and layout solver behavior.

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../features/taxonomy-view/page/leaf/LeafDeckScene", () => ({
  LeafDeckScene: ({
    initialViewport,
    scene,
  }: {
    readonly initialViewport: {
      readonly target: readonly [number, number, number];
      readonly zoom: number;
    };
    readonly scene: {
      readonly edges: ReadonlyArray<unknown>;
      readonly pointNodes: ReadonlyArray<unknown>;
    };
  }) => (
    <div data-testid="layout-lab-production-scene">
      <div data-testid="layout-lab-point-count">{scene.pointNodes.length}</div>
      <div data-testid="layout-lab-edge-count">{scene.edges.length}</div>
      <div data-testid="layout-lab-initial-target">
        {initialViewport.target.join(",")}
      </div>
    </div>
  ),
}));

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../features/taxonomy-view/data/taxonomyViewQueries";
import { TaxonomyLayoutLabPreview } from "./TaxonomyLayoutLabPreview";

describe("TaxonomyLayoutLabPreview", () => {
  it("renders layout data through the production leaf scene component", () => {
    const layout: TaxonomyCardScopeLayoutSliceResponse = {
      edges: [[1, 2, 0.9]],
      layout_status: "ready",
      layout_version: "taxonomy-card-scope-layout-v1",
      nodes: [
        { id: 1, scope: "inner", x: -10, y: 0 },
        { id: 2, scope: "outer", x: 30, y: 20 },
      ],
      parent_taxonomy_node_id: null,
      requested_bounds: {
        max_x: 30,
        max_y: 20,
        min_x: -10,
        min_y: 0,
      },
      route_path: "layout-lab/obsidian-sample",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 1,
    };

    render(<TaxonomyLayoutLabPreview layout={layout} />);

    expect(screen.getByTestId("layout-lab-production-scene")).toBeTruthy();
    expect(screen.getByTestId("layout-lab-point-count")).toHaveTextContent("2");
    expect(screen.getByTestId("layout-lab-edge-count")).toHaveTextContent("1");
    expect(screen.getByTestId("layout-lab-initial-target")).toHaveTextContent(
      "10,10,0",
    );
  });

  it("renders an empty state before a layout has loaded", () => {
    render(<TaxonomyLayoutLabPreview layout={null} />);

    expect(screen.getByTestId("layout-lab-empty-preview")).toBeTruthy();
  });
});
