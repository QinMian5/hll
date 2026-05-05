// abstract: Unit tests for the taxonomy layout lab application shell.
// out_of_scope: Real deck.gl rendering and backend force simulation.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../features/taxonomy-view/data/taxonomyViewQueries";
import type { TaxonomyLayoutLabParams } from "./taxonomyLayoutLabParams";

const apiMocks = vi.hoisted(() => ({
  fetchLayoutLabDefaultParams: vi.fn(),
  fetchLayoutLabFixtures: vi.fn(),
  solveLayoutLab: vi.fn(),
}));

vi.mock("./taxonomyLayoutLabApi", () => ({
  DEFAULT_LAYOUT_LAB_API_BASE_URL: "http://127.0.0.1:8765",
  fetchLayoutLabDefaultParams: apiMocks.fetchLayoutLabDefaultParams,
  fetchLayoutLabFixtures: apiMocks.fetchLayoutLabFixtures,
  solveLayoutLab: apiMocks.solveLayoutLab,
}));

vi.mock("./TaxonomyLayoutLabPreview", () => ({
  TaxonomyLayoutLabPreview: ({
    layout,
  }: {
    readonly layout: TaxonomyCardScopeLayoutSliceResponse | null;
  }) => (
    <div data-testid="layout-lab-preview">{layout?.route_path ?? "empty"}</div>
  ),
}));

import { TaxonomyLayoutLabApp } from "./TaxonomyLayoutLabApp";

const defaultParams: TaxonomyLayoutLabParams = {
  alpha_min: 0.001,
  center_gravity_strength: 0.1,
  charge_strength: -180,
  collision_radius: 16,
  collision_strength: 0.92,
  link_base_distance: 92,
  link_base_strength: 1.05,
  link_distance_strength_factor: 36,
  link_strength_factor: 0.5,
  radial_boundary_radius: 0,
  radial_boundary_strength: 0,
  seed_base_radius: 80,
  seed_radius_step: 96,
  simulation_ticks: 160,
  velocity_retention: 0.55,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  apiMocks.fetchLayoutLabFixtures.mockResolvedValue([
    {
      edge_count: 2158,
      name: "prod-heat-thermodynamics",
      node_count: 1233,
    },
    {
      edge_count: 18,
      name: "obsidian-sample",
      node_count: 16,
    },
  ]);
  apiMocks.fetchLayoutLabDefaultParams.mockResolvedValue(defaultParams);
  apiMocks.solveLayoutLab.mockResolvedValue(
    makeLayout("layout-lab/obsidian-sample"),
  );
});

describe("TaxonomyLayoutLabApp", () => {
  it("selects the small sample fixture without automatically solving it", async () => {
    render(<TaxonomyLayoutLabApp />);

    const fixtureSelect = await screen.findByLabelText("Fixture");

    expect(fixtureSelect).toHaveValue("obsidian-sample");
    expect(screen.getByText("16 nodes / 18 edges")).toBeInTheDocument();
    expect(screen.getByTestId("layout-lab-preview")).toHaveTextContent("empty");
    expect(apiMocks.solveLayoutLab).not.toHaveBeenCalled();
  });

  it("runs the production solve path only after the operator clicks Solve", async () => {
    render(<TaxonomyLayoutLabApp />);

    await screen.findByLabelText("Fixture");
    fireEvent.click(screen.getByRole("button", { name: "Solve" }));

    await waitFor(() => {
      expect(apiMocks.solveLayoutLab).toHaveBeenCalledTimes(1);
    });
    expect(apiMocks.solveLayoutLab).toHaveBeenCalledWith(
      expect.objectContaining({
        apiBaseUrl: "http://127.0.0.1:8765",
        fixtureName: "obsidian-sample",
        params: defaultParams,
      }),
    );
    expect(await screen.findByTestId("layout-lab-preview")).toHaveTextContent(
      "layout-lab/obsidian-sample",
    );
  });

  it("keeps slider edits pending until Solve is clicked again", async () => {
    render(<TaxonomyLayoutLabApp />);

    await screen.findByLabelText("Fixture");
    fireEvent.change(screen.getByLabelText("Simulation ticks"), {
      target: { value: "12" },
    });

    expect(apiMocks.solveLayoutLab).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Solve" }));

    await waitFor(() => {
      expect(apiMocks.solveLayoutLab).toHaveBeenCalledTimes(1);
    });
    expect(apiMocks.solveLayoutLab).toHaveBeenCalledWith(
      expect.objectContaining({
        params: expect.objectContaining({ simulation_ticks: 12 }),
      }),
    );
  });
});

function makeLayout(routePath: string): TaxonomyCardScopeLayoutSliceResponse {
  return {
    edges: [[1, 2, 1]],
    layout_status: "ready",
    layout_version: "taxonomy-card-scope-layout-v2",
    nodes: [
      { id: 1, scope: "inner", x: 0, y: 0 },
      { id: 2, scope: "outer", x: 10, y: 10 },
    ],
    parent_taxonomy_node_id: null,
    requested_bounds: {
      max_x: 10,
      max_y: 10,
      min_x: 0,
      min_y: 0,
    },
    route_path: routePath,
    scope_kind: "taxonomy_node",
    taxonomy_node_id: 1,
  };
}
