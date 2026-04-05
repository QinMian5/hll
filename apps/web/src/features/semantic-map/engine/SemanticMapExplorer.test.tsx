// abstract: Behavior tests for semantic-map point inspection in explorer state.
// out_of_scope: DeckGL rendering internals and HTTP request integration behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  SemanticMapManifestViewModel,
  SemanticMapPointViewModel,
  SemanticMapTileViewModel,
} from "../data/mappers";
import { SemanticMapExplorer } from "./SemanticMapExplorer";

const mockedSemanticMapRegionTileQuery = vi.hoisted(() => vi.fn());

vi.mock("../data/semanticMapQueries", () => ({
  useSemanticMapRegionTileQuery: mockedSemanticMapRegionTileQuery,
}));

vi.mock("./SemanticMapCanvas", () => ({
  SemanticMapCanvas: (props: {
    onPointSelect: (point: SemanticMapPointViewModel | null) => void;
    tile: SemanticMapTileViewModel | null;
  }) => (
    <div>
      <button
        onClick={() => props.onPointSelect(props.tile?.points[0] ?? null)}
        type="button"
      >
        select-first-point
      </button>
      <button onClick={() => props.onPointSelect(null)} type="button">
        clear-point
      </button>
    </div>
  ),
}));

function makeManifest(): SemanticMapManifestViewModel {
  return {
    builtAt: "2026-04-03T13:45:00Z",
    coordinateSystem: {
      axisDirection: "x-right-y-up",
      boundsFormat: "min_x_min_y_max_x_max_y",
      kind: "cartesian2d",
    },
    defaultSemanticLevel: 0,
    defaultView: {
      target: [500, 500],
      zoom: 0,
    },
    levels: [
      {
        childContentRole: "taxonomy_region",
        displayName: "Taxonomy D0",
        level: 0,
        maxZoom: 1,
        minZoom: 0,
        regionRole: "taxonomy_region",
        stableId: "taxonomy_depth_0",
      },
    ],
    maxZoom: 6,
    schemaVersion: "20260403_134500_000123",
    tileSize: 512,
    version: "20260403_134500_000123",
    worldBounds: [0, 0, 1000, 1000],
  };
}

function makeTile(
  points: SemanticMapTileViewModel["points"],
  edges: SemanticMapTileViewModel["edges"] = [],
): SemanticMapTileViewModel {
  return {
    edges,
    labels: [],
    points,
    regions: [],
    schemaVersion: "20260403_134500_000123",
    semanticLevel: 0,
    stats: {
      edgeCount: edges.length,
      labelCount: 0,
      regionCount: 0,
    },
    tile: {
      boundsFormat: "min_x_min_y_max_x_max_y",
      tileBounds: [0, 0, 1000, 1000],
      x: 0,
      y: 0,
      z: 0,
    },
    version: "20260403_134500_000123",
  };
}

describe("SemanticMapExplorer point inspection", () => {
  afterEach(() => {
    cleanup();
    mockedSemanticMapRegionTileQuery.mockReset();
  });

  it("shows explicit no-point state when current tile has no points", () => {
    mockedSemanticMapRegionTileQuery.mockReturnValue({
      data: makeTile([]),
      error: null,
      isError: false,
      isPending: false,
    });

    render(<SemanticMapExplorer manifest={makeManifest()} />);

    expect(
      screen.getByText(/No points are available in the current tile./i),
    ).toBeInTheDocument();
  });

  it("shows selected point details after explicit point selection", () => {
    mockedSemanticMapRegionTileQuery.mockReturnValue({
      data: makeTile([
        {
          id: "card:7",
          leafRegionId: "taxonomy:12",
          nodeId: 7,
          position: [510, 500],
          title: "Card Alpha",
        },
      ]),
      error: null,
      isError: false,
      isPending: false,
    });

    render(<SemanticMapExplorer manifest={makeManifest()} />);

    expect(
      screen.getByText(/Click a point to inspect card details./i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "select-first-point" }));

    expect(screen.getByText("Card Alpha")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("taxonomy:12")).toBeInTheDocument();
    expect(
      screen.getByText(/No connected cards in the current tile./i),
    ).toBeInTheDocument();
  });

  it("shows connected-card details for the selected point", () => {
    mockedSemanticMapRegionTileQuery.mockReturnValue({
      data: makeTile(
        [
          {
            id: "card:7",
            leafRegionId: "taxonomy:12",
            nodeId: 7,
            position: [510, 500],
            title: "Card Alpha",
          },
          {
            id: "card:11",
            leafRegionId: "taxonomy:12",
            nodeId: 11,
            position: [540, 500],
            title: "Card Beta",
          },
        ],
        [
          {
            id: "edge:7:11",
            sourceNodeId: 7,
            sourcePosition: [510, 500],
            strength: 0.91,
            targetNodeId: 11,
            targetPosition: [540, 500],
          },
        ],
      ),
      error: null,
      isError: false,
      isPending: false,
    });

    render(<SemanticMapExplorer manifest={makeManifest()} />);
    fireEvent.click(screen.getByRole("button", { name: "select-first-point" }));

    expect(screen.getByText(/Connected cards/i)).toBeInTheDocument();
    expect(screen.getByText("Card Beta")).toBeInTheDocument();
  });
});
