// abstract: Behavior tests for semantic-map page empty-state handling.
// out_of_scope: deck.gl rendering internals and end-to-end browser behavior.

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";

function makeManifestResponse() {
  return new Response(
    JSON.stringify({
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
    }),
    {
      headers: { "Content-Type": "application/json" },
      status: 200,
    },
  );
}

function makeTileResponse() {
  return new Response(
    JSON.stringify({
      edges: [],
      labels: [],
      points: [],
      regions: [],
      schema_version: "20260403_134500_000123",
      semantic_level: 0,
      stats: {
        edge_count: 0,
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
    }),
    {
      headers: { "Content-Type": "application/json" },
      status: 200,
    },
  );
}

function makeNonEmptyTileResponse() {
  return new Response(
    JSON.stringify({
      edges: [
        {
          id: "edge:1:2",
          source_node_id: 1,
          source_position: [520, 510],
          strength: 0.87,
          target_node_id: 2,
          target_position: [560, 530],
        },
      ],
      labels: [
        {
          font_size: 16,
          id: "label-domain-alpha",
          label_rank: 1,
          position: [500, 500],
          region_id: "region-domain-alpha",
          text: "Alpha Domain",
        },
      ],
      points: [
        {
          id: "card-1",
          leaf_region_id: "region-domain-alpha",
          node_id: 1,
          position: [520, 510],
          title: "Alpha card",
        },
      ],
      regions: [
        {
          bbox: [200, 200, 800, 800],
          centroid: [500, 500],
          children_available: true,
          display_rank: 1,
          geometry: {
            coordinates: [
              [200, 200],
              [800, 200],
              [800, 800],
              [200, 800],
            ],
            type: "polygon",
          },
          id: "region-domain-alpha",
          parent_id: null,
          region_name: "Alpha Domain",
        },
      ],
      schema_version: "20260403_134500_000123",
      semantic_level: 0,
      stats: {
        edge_count: 1,
        label_count: 1,
        region_count: 1,
      },
      tile: {
        bounds_format: "min_x_min_y_max_x_max_y",
        tile_bounds: [0, 0, 1000, 1000],
        x: 0,
        y: 0,
        z: 0,
      },
      version: "20260403_134500_000123",
    }),
    {
      headers: { "Content-Type": "application/json" },
      status: 200,
    },
  );
}

describe("SemanticMapPage", () => {
  afterEach(() => {
    vi.doUnmock("../engine/SemanticMapExplorer");
    vi.unstubAllEnvs();
    vi.resetModules();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  async function renderSemanticMapPage() {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:3000");
    const module = await import("./SemanticMapPage");

    render(
      <AppProviders>
        <module.SemanticMapPage />
      </AppProviders>,
    );
  }

  it("renders the empty state when no snapshot is available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND",
              details: {},
              hint: "Rebuild semantic-map artifacts and retry.",
              message: "No semantic-map snapshot is currently available.",
              request_id: "req_test_snapshot_missing",
            },
          }),
          {
            headers: { "Content-Type": "application/json" },
            status: 404,
          },
        ),
      ),
    );

    await renderSemanticMapPage();

    expect(
      await screen.findByText(/snapshot unavailable/i),
    ).toBeInTheDocument();
  });

  it("renders debug metadata for the pinned snapshot and semantic level", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(makeManifestResponse())
        .mockResolvedValueOnce(makeTileResponse()),
    );

    await renderSemanticMapPage();

    expect(await screen.findByText(/current version/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/active semantic level/i),
    ).toBeInTheDocument();
  });

  it("shows an engine loading fallback while the semantic-map bundle resolves", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(makeManifestResponse())
        .mockResolvedValueOnce(makeTileResponse()),
    );
    vi.doMock("../engine/SemanticMapExplorer", async () => {
      await new Promise((resolve) => {
        setTimeout(resolve, 50);
      });

      return {
        SemanticMapExplorer: () => <div>Semantic map engine ready</div>,
      };
    });

    await renderSemanticMapPage();

    expect(await screen.findByText(/loading map engine/i)).toBeInTheDocument();
    expect(
      await screen.findByText(/semantic map engine ready/i),
    ).toBeInTheDocument();
  });

  it("pins tile reads to the current snapshot version and shows real region counts", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(makeManifestResponse())
      .mockResolvedValueOnce(makeNonEmptyTileResponse());
    vi.stubGlobal("fetch", fetchMock);

    await renderSemanticMapPage();

    expect(await screen.findByText(/1 regions/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const tileRequest = fetchMock.mock.calls[1]?.[0];
    expect(tileRequest).toBeInstanceOf(Request);
    if (!(tileRequest instanceof Request)) {
      throw new Error(
        "Expected the semantic-map tile read to use a Request object.",
      );
    }
    expect(tileRequest.url).toContain(
      "/semantic-map/versions/20260403_134500_000123/tiles/regions/0/0/0/0",
    );
  });
});
