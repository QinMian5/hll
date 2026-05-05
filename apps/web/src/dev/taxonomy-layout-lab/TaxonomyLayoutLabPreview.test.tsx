// abstract: Unit tests for the standalone taxonomy layout lab preview.
// out_of_scope: Real WebGL rendering and layout solver behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const leafSceneRenderCount = vi.hoisted(() => ({ current: 0 }));

vi.mock("../../features/taxonomy-view/page/leaf/LeafDeckScene", async () => {
  const React = await vi.importActual<typeof import("react")>("react");

  return {
    LeafDeckScene: ({
      initialViewport,
      onViewportChange,
      scene,
    }: {
      readonly initialViewport: {
        readonly target: readonly [number, number, number];
        readonly zoom: number;
      };
      readonly onViewportChange: (viewport: {
        readonly target: readonly [number, number, number];
        readonly zoom: number;
      }) => void;
      readonly scene: {
        readonly edges: ReadonlyArray<unknown>;
        readonly pointNodes: ReadonlyArray<unknown>;
      };
    }) => {
      leafSceneRenderCount.current += 1;
      React.useEffect(() => {
        onViewportChange({
          target: [...initialViewport.target] as const,
          zoom: initialViewport.zoom,
        });
      }, [initialViewport, onViewportChange]);

      return (
        <div data-testid="layout-lab-production-scene">
          <div data-testid="layout-lab-point-count">
            {scene.pointNodes.length}
          </div>
          <div data-testid="layout-lab-edge-count">{scene.edges.length}</div>
          <div data-testid="layout-lab-initial-target">
            {initialViewport.target.join(",")}
          </div>
        </div>
      );
    },
  };
});

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../features/taxonomy-view/data/taxonomyViewQueries";
import { TaxonomyLayoutLabPreview } from "./TaxonomyLayoutLabPreview";

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  leafSceneRenderCount.current = 0;
});

describe("TaxonomyLayoutLabPreview", () => {
  it("renders layout data through the production leaf scene component", () => {
    const layout: TaxonomyCardScopeLayoutSliceResponse = {
      edges: [[1, 2, 0.9]],
      layout_status: "ready",
      layout_version: "taxonomy-card-scope-layout-v2",
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

  it("does not feed production viewport snapshots back into initial viewport", async () => {
    const layout: TaxonomyCardScopeLayoutSliceResponse = {
      edges: [[1, 2, 0.9]],
      layout_status: "ready",
      layout_version: "taxonomy-card-scope-layout-v2",
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

    await waitFor(() => {
      expect(leafSceneRenderCount.current).toBe(1);
    });
  });

  it("keeps the initial viewport stable while the same fixture is re-solved", () => {
    const initialLayout: TaxonomyCardScopeLayoutSliceResponse = {
      edges: [[1, 2, 0.9]],
      layout_status: "ready",
      layout_version: "taxonomy-card-scope-layout-v2",
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
      route_path: "layout-lab/prod-heat-thermodynamics",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 1,
    };
    const reSolvedLayout: TaxonomyCardScopeLayoutSliceResponse = {
      ...initialLayout,
      nodes: [
        { id: 1, scope: "inner", x: 900, y: 950 },
        { id: 2, scope: "outer", x: 1100, y: 1050 },
        { id: 3, scope: "outer", x: 1150, y: 1120 },
      ],
      requested_bounds: {
        max_x: 1150,
        max_y: 1120,
        min_x: 900,
        min_y: 950,
      },
    };

    const { rerender } = render(
      <TaxonomyLayoutLabPreview layout={initialLayout} />,
    );

    expect(screen.getByTestId("layout-lab-initial-target")).toHaveTextContent(
      "10,10,0",
    );

    rerender(<TaxonomyLayoutLabPreview layout={reSolvedLayout} />);

    expect(screen.getByTestId("layout-lab-point-count")).toHaveTextContent("3");
    expect(screen.getByTestId("layout-lab-initial-target")).toHaveTextContent(
      "10,10,0",
    );
  });

  it("resets the initial viewport when the selected fixture changes", () => {
    const initialLayout: TaxonomyCardScopeLayoutSliceResponse = {
      edges: [[1, 2, 0.9]],
      layout_status: "ready",
      layout_version: "taxonomy-card-scope-layout-v2",
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
      route_path: "layout-lab/prod-heat-thermodynamics",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 1,
    };
    const nextFixtureLayout: TaxonomyCardScopeLayoutSliceResponse = {
      ...initialLayout,
      requested_bounds: {
        max_x: 1150,
        max_y: 1120,
        min_x: 900,
        min_y: 950,
      },
      route_path: "layout-lab/obsidian-sample",
    };

    const { rerender } = render(
      <TaxonomyLayoutLabPreview layout={initialLayout} />,
    );

    rerender(<TaxonomyLayoutLabPreview layout={nextFixtureLayout} />);

    expect(screen.getByTestId("layout-lab-initial-target")).toHaveTextContent(
      "1025,1035,0",
    );
  });

  it("renders an empty state before a layout has loaded", () => {
    render(<TaxonomyLayoutLabPreview layout={null} />);

    expect(screen.getByTestId("layout-lab-empty-preview")).toBeTruthy();
  });
});
