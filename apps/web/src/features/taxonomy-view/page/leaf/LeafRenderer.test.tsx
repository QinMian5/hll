// abstract: Behavior tests for leaf renderer title labels, point interaction, and disclosure state.
// out_of_scope: Real deck.gl WebGL rendering and browser-level interaction fidelity.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LEAF_POINT_TITLE_ACTIVATION_ZOOM } from "./leafRendererConfig";

vi.mock("../../data/taxonomyViewQueries", () => ({
  useTaxonomyLeafLayoutSliceQuery: vi.fn(),
  useTaxonomyLeafNodeDetailsQuery: vi.fn(),
  useTaxonomyLeafNodeTitlesQuery: vi.fn(),
}));

vi.mock("./LeafDeckScene", () => ({
  LeafDeckScene: ({
    activeFocusNodeId,
    hoveredPointNodeId,
    isPointInteractionEnabled,
    onCanvasClick,
    onPointClick,
    onPointHover,
    onViewportFrameChange,
    onViewportChange,
    scene,
  }: {
    readonly activeFocusNodeId: number | null;
    readonly hoveredPointNodeId: number | null;
    readonly isPointInteractionEnabled: boolean;
    readonly onCanvasClick: () => void;
    readonly onPointClick: (nodeId: number) => void;
    readonly onPointHover: (nodeId: number | null) => void;
    readonly onViewportFrameChange?: (viewport: {
      readonly target: readonly [number, number, number];
      readonly zoom: number;
    }) => void;
    readonly onViewportChange: (viewport: {
      readonly target: readonly [number, number, number];
      readonly zoom: number;
    }) => void;
    readonly scene: {
      readonly edges: ReadonlyArray<unknown>;
      readonly pointNodes: ReadonlyArray<unknown>;
      readonly titleLabelNodes: ReadonlyArray<unknown>;
    };
  }) => (
    <div data-testid="leaf-deck-scene-mock">
      <div data-testid="leaf-active-focus-node-id">
        {activeFocusNodeId ?? "none"}
      </div>
      <div data-testid="leaf-hovered-point-node-id">
        {hoveredPointNodeId ?? "none"}
      </div>
      <div data-testid="leaf-point-interaction-enabled">
        {String(isPointInteractionEnabled)}
      </div>
      <div data-testid="leaf-scene-point-count">{scene.pointNodes.length}</div>
      <div data-testid="leaf-scene-title-label-count">
        {scene.titleLabelNodes.length}
      </div>
      <div data-testid="leaf-scene-edge-count">{scene.edges.length}</div>
      <button
        onClick={() =>
          onViewportChange({
            target: [700, 450, 0],
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM,
          })
        }
        type="button"
      >
        Zoom in
      </button>
      <button
        onClick={() =>
          onViewportChange({
            target: [700, 450, 0],
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM - 0.1,
          })
        }
        type="button"
      >
        Zoom out
      </button>
      <button
        onClick={() =>
          onViewportFrameChange?.({
            target: [740, 480, 0],
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM,
          })
        }
        type="button"
      >
        Frame move
      </button>
      <button
        onClick={() => {
          if (isPointInteractionEnabled) {
            onPointHover(10);
          }
        }}
        type="button"
      >
        Hover 10
      </button>
      <button
        onClick={() => {
          if (isPointInteractionEnabled) {
            onPointHover(11);
          }
        }}
        type="button"
      >
        Hover 11
      </button>
      <button
        onClick={() => {
          if (isPointInteractionEnabled) {
            onPointHover(null);
          }
        }}
        type="button"
      >
        Leave point
      </button>
      <button
        onClick={() => {
          if (isPointInteractionEnabled) {
            onPointClick(10);
          }
        }}
        type="button"
      >
        Click 10
      </button>
      <button onClick={onCanvasClick} type="button">
        Click canvas
      </button>
    </div>
  ),
}));

import type {
  TaxonomyLeafLayoutSliceResponse,
  TaxonomyLeafNodeDetailsResponse,
  TaxonomyLeafNodeTitlesResponse,
  TaxonomyLeafView,
} from "../../data/taxonomyViewQueries";
import * as taxonomyViewQueries from "../../data/taxonomyViewQueries";
import { LeafRenderer } from "./LeafRenderer";

const mockUseTaxonomyLeafLayoutSliceQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyLeafLayoutSliceQuery,
);
const mockUseTaxonomyLeafNodeDetailsQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyLeafNodeDetailsQuery,
);
const mockUseTaxonomyLeafNodeTitlesQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyLeafNodeTitlesQuery,
);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function parseProjectedTransform(transform: string) {
  const match = transform.match(
    /translate3d\(([-\d.]+)px,\s*([-\d.]+)px,\s*0px\)/,
  );

  if (!match) {
    throw new Error(`Unexpected transform: ${transform}`);
  }

  return {
    x: Number.parseFloat(match[1] ?? "0"),
    y: Number.parseFloat(match[2] ?? "0"),
  };
}

function makeLeafView(): TaxonomyLeafView {
  return {
    breadcrumb: [],
    current_node: {
      depth: 2,
      id: 2,
      is_leaf: true,
      name: "Algebra",
      parent_id: 1,
    },
    edge_count: 1,
    generated_at: "2026-04-29T00:00:00Z",
    layout_version: "taxonomy-leaf-layout-v1",
    node_kind: "leaf",
    node_count: 2,
    world_bounds: { max_x: 744, max_y: 484, min_x: 696, min_y: 446 },
  };
}

function makeLeafLayoutSliceResponse(): TaxonomyLeafLayoutSliceResponse {
  return {
    edges: [[10, 11, 0.8]],
    layout_version: "taxonomy-leaf-layout-v1",
    leaf_id: 2,
    nodes: [
      { id: 10, scope: "inner", x: 700, y: 450 },
      { id: 11, scope: "outer", x: 740, y: 480 },
    ],
    requested_bounds: { max_x: 1562, max_y: 1060, min_x: -162, min_y: -160 },
  };
}

function makeLeafTitlesResponse(): TaxonomyLeafNodeTitlesResponse {
  return {
    nodes: [
      { id: 10, title: "Equation \\(E=mc^2\\)" },
      { id: 11, title: "Proof" },
    ],
  };
}

function makeLeafDetailsResponse(
  nodeIds: readonly number[],
): TaxonomyLeafNodeDetailsResponse {
  const detailsById: Record<
    number,
    TaxonomyLeafNodeDetailsResponse["nodes"][number]
  > = {
    10: {
      content: "*Equation* content",
      current_version: 3,
      id: 10,
      title: "Equation \\(E=mc^2\\)",
    },
    11: {
      content: "Proof content",
      current_version: 5,
      id: 11,
      title: "Proof",
    },
  };

  return {
    nodes: nodeIds.flatMap((nodeId) => {
      const detail = detailsById[nodeId];

      return detail ? [detail] : [];
    }),
  };
}

function installSuccessfulQueryMocks() {
  mockUseTaxonomyLeafLayoutSliceQuery.mockImplementation(
    (_leafId, _bounds, options) =>
      ({
        data: options.enabled ? makeLeafLayoutSliceResponse() : undefined,
        error: null,
        isError: false,
        isPending: false,
      }) as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyLeafLayoutSliceQuery
      >,
  );
  mockUseTaxonomyLeafNodeTitlesQuery.mockImplementation(
    (_leafId, _nodeIds, options) =>
      ({
        data: options.enabled ? makeLeafTitlesResponse() : undefined,
        error: null,
        isError: false,
        isPending: false,
      }) as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyLeafNodeTitlesQuery
      >,
  );
  mockUseTaxonomyLeafNodeDetailsQuery.mockImplementation(
    (_leafId, nodeIds, options) =>
      ({
        data: options.enabled ? makeLeafDetailsResponse(nodeIds) : undefined,
        error: null,
        isError: false,
        isPending: false,
      }) as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyLeafNodeDetailsQuery
      >,
  );
}

describe("LeafRenderer", () => {
  it("renders non-interactive points before the title zoom without title or detail hydration", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    expect(
      await screen.findByTestId("leaf-scene-point-count"),
    ).toHaveTextContent("2");
    expect(
      screen.getByTestId("leaf-scene-title-label-count"),
    ).toHaveTextContent("0");
    expect(screen.getByTestId("leaf-scene-edge-count")).toHaveTextContent("1");
    expect(
      screen.getByTestId("leaf-point-interaction-enabled"),
    ).toHaveTextContent("false");
    expect(mockUseTaxonomyLeafLayoutSliceQuery).toHaveBeenCalledWith(
      2,
      {
        max_x: 1562,
        max_y: 1060,
        min_x: -162,
        min_y: -160,
      },
      expect.objectContaining({ enabled: true }),
    );
    expect(mockUseTaxonomyLeafNodeTitlesQuery).toHaveBeenCalledWith(
      2,
      [],
      expect.objectContaining({ enabled: false }),
    );
    expect(mockUseTaxonomyLeafNodeDetailsQuery).toHaveBeenCalledWith(
      2,
      [],
      expect.objectContaining({ enabled: false }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Hover 10" }));
    fireEvent.click(screen.getByRole("button", { name: "Click 10" }));

    expect(screen.getByTestId("leaf-active-focus-node-id")).toHaveTextContent(
      "none",
    );
  });

  it("hydrates title labels at zoom 2 and moves the hovered title into the hover disclosure", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));

    await waitFor(() => {
      expect(mockUseTaxonomyLeafNodeTitlesQuery).toHaveBeenCalledWith(
        2,
        expect.arrayContaining([10, 11]),
        expect.objectContaining({ enabled: true }),
      );
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-scene-title-label-count"),
      ).toHaveTextContent("2");
    });

    const firstLabel = screen.getByTestId("taxonomy-leaf-title-label-10");

    expect(firstLabel).toHaveTextContent("Equation");
    expect(firstLabel).toHaveStyle({ opacity: "1" });
    expect(document.querySelector(".katex")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Hover 10" }));

    await waitFor(() => {
      expect(mockUseTaxonomyLeafNodeDetailsQuery).toHaveBeenCalledWith(
        2,
        [10],
        expect.objectContaining({ enabled: true }),
      );
    });

    const disclosure = await screen.findByTestId(
      "taxonomy-leaf-disclosure-overlay",
    );

    expect(disclosure).toHaveAttribute("data-disclosure-mode", "hover");
    expect(disclosure).toHaveTextContent("Equation");
    expect(disclosure).toHaveTextContent("Equation content");
    expect(screen.getByTestId("leaf-active-focus-node-id")).toHaveTextContent(
      "10",
    );
    expect(firstLabel).toHaveStyle({ opacity: "0" });
  });

  it("shows selected disclosure with title, hides that label, and toggles selection from the point", async () => {
    installSuccessfulQueryMocks();
    const onSuggestEdit = vi.fn();

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        onSuggestEdit={onSuggestEdit}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));
    await screen.findByTestId("taxonomy-leaf-title-label-10");

    fireEvent.click(screen.getByRole("button", { name: "Click 10" }));

    const selectedDisclosure = await screen.findByTestId(
      "taxonomy-leaf-disclosure-overlay",
    );

    expect(selectedDisclosure).toHaveAttribute(
      "data-disclosure-mode",
      "selected",
    );
    expect(selectedDisclosure).toHaveTextContent("Equation");
    expect(selectedDisclosure).toHaveTextContent("Equation content");
    expect(screen.getByTestId("taxonomy-leaf-title-label-10")).toHaveStyle({
      opacity: "0",
    });

    const editButton = screen.getByTestId(
      "taxonomy-leaf-disclosure-edit-button",
    );

    expect(editButton).toHaveAttribute(
      "aria-label",
      "Suggest edit for Equation \\(E=mc^2\\)",
    );

    fireEvent.click(editButton);

    expect(onSuggestEdit).toHaveBeenCalledWith({
      content: "*Equation* content",
      currentVersion: 3,
      nodeId: 10,
      title: "Equation \\(E=mc^2\\)",
    });

    fireEvent.click(screen.getByRole("button", { name: "Click 10" }));

    await waitFor(() => {
      expect(
        screen.queryByTestId("taxonomy-leaf-disclosure-overlay"),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("taxonomy-leaf-title-label-10")).toHaveStyle({
      opacity: "1",
    });
  });

  it("keeps selected as the graph focus while another point is hovered, then falls back to hover after clearing selected", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));
    await screen.findByTestId("taxonomy-leaf-title-label-10");

    fireEvent.click(screen.getByRole("button", { name: "Click 10" }));
    await screen.findByTestId("taxonomy-leaf-disclosure-overlay");
    fireEvent.click(screen.getByRole("button", { name: "Hover 11" }));

    expect(screen.getByTestId("leaf-hovered-point-node-id")).toHaveTextContent(
      "11",
    );
    expect(screen.getByTestId("leaf-active-focus-node-id")).toHaveTextContent(
      "10",
    );
    expect(
      screen.getByTestId("taxonomy-leaf-disclosure-overlay"),
    ).toHaveTextContent("Equation");
    expect(
      screen.getByTestId("taxonomy-leaf-disclosure-overlay"),
    ).not.toHaveTextContent("Proof content");
    expect(screen.getByTestId("taxonomy-leaf-title-label-10")).toHaveStyle({
      opacity: "0",
    });
    expect(screen.getByTestId("taxonomy-leaf-title-label-11")).toHaveStyle({
      opacity: "1",
    });

    fireEvent.click(screen.getByRole("button", { name: "Click canvas" }));

    await waitFor(() => {
      expect(screen.getByTestId("leaf-active-focus-node-id")).toHaveTextContent(
        "11",
      );
    });
    expect(
      screen.getByTestId("taxonomy-leaf-disclosure-overlay"),
    ).toHaveTextContent("Proof");
    expect(
      screen.getByTestId("taxonomy-leaf-disclosure-overlay"),
    ).toHaveTextContent("Proof content");
    expect(screen.getByTestId("taxonomy-leaf-title-label-11")).toHaveStyle({
      opacity: "0",
    });
  });

  it("clears hover and selected state when returning below the title zoom", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));
    await screen.findByTestId("taxonomy-leaf-title-label-10");
    fireEvent.click(screen.getByRole("button", { name: "Click 10" }));
    await screen.findByTestId("taxonomy-leaf-disclosure-overlay");

    fireEvent.click(screen.getByRole("button", { name: "Zoom out" }));

    await waitFor(() => {
      expect(screen.getByTestId("leaf-active-focus-node-id")).toHaveTextContent(
        "none",
      );
    });
    expect(
      screen.getByTestId("leaf-scene-title-label-count"),
    ).toHaveTextContent("0");
    expect(
      screen.queryByTestId("taxonomy-leaf-disclosure-overlay"),
    ).not.toBeInTheDocument();
  });

  it("keeps labels visually synced with live viewport frame updates", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));

    const firstLabel = await screen.findByTestId(
      "taxonomy-leaf-title-label-10",
    );
    const beforeFrameMove = parseProjectedTransform(firstLabel.style.transform);

    expect(beforeFrameMove.x).toBeGreaterThan(0);
    expect(beforeFrameMove.y).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Frame move" }));

    const afterFrameMove = parseProjectedTransform(firstLabel.style.transform);

    expect(afterFrameMove.x).not.toBeCloseTo(beforeFrameMove.x, 4);
    expect(afterFrameMove.y).not.toBeCloseTo(beforeFrameMove.y, 4);
  });
});
