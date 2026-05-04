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
  useTaxonomyCardScopeLayoutSliceQuery: vi.fn(),
  useTaxonomyCardScopeNodeDetailsQuery: vi.fn(),
  useTaxonomyCardScopeNodeTitlesQuery: vi.fn(),
}));

vi.mock("./LeafDeckScene", () => ({
  LeafDeckScene: ({
    activeFocusNodeId,
    disclosure,
    hiddenLabelNodeId,
    hoveredPointNodeId,
    initialViewport,
    isPointInteractionEnabled,
    onSuggestEdit,
    onCanvasClick,
    onPointClick,
    onPointHover,
    onViewportFrameChange,
    onViewportChange,
    scene,
  }: {
    readonly activeFocusNodeId: number | null;
    readonly disclosure?: {
      readonly mode: "hover" | "selected";
      readonly node: {
        readonly content: string;
        readonly currentVersion: number;
        readonly graphNodeId: number;
        readonly title: string;
      };
    } | null;
    readonly hiddenLabelNodeId: number | null;
    readonly hoveredPointNodeId: number | null;
    readonly initialViewport: {
      readonly target: readonly [number, number, number];
      readonly zoom: number;
    };
    readonly isPointInteractionEnabled: boolean;
    readonly onCanvasClick: () => void;
    readonly onSuggestEdit?: (card: {
      readonly content: string;
      readonly currentVersion: number;
      readonly nodeId: number;
      readonly title: string;
    }) => void;
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
      readonly pointNodes: ReadonlyArray<{ readonly radius?: number }>;
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
      <div data-testid="leaf-hidden-label-node-id">
        {hiddenLabelNodeId ?? "none"}
      </div>
      <div data-testid="leaf-initial-viewport-zoom">{initialViewport.zoom}</div>
      <div data-testid="leaf-point-interaction-enabled">
        {String(isPointInteractionEnabled)}
      </div>
      <div data-testid="leaf-scene-point-count">{scene.pointNodes.length}</div>
      <div data-testid="leaf-scene-first-point-radius">
        {scene.pointNodes[0]?.radius ?? "none"}
      </div>
      <div data-testid="leaf-scene-title-label-count">
        {scene.titleLabelNodes.length}
      </div>
      <div data-testid="leaf-scene-edge-count">{scene.edges.length}</div>
      {disclosure ? (
        <div
          data-disclosure-mode={disclosure.mode}
          data-testid="taxonomy-leaf-disclosure-overlay"
        >
          <span>{disclosure.node.title}</span>
          <span>{disclosure.node.content.replaceAll("*", "")}</span>
          {onSuggestEdit ? (
            <button
              aria-label={`Suggest edit for ${disclosure.node.title}`}
              data-testid="taxonomy-leaf-disclosure-edit-button"
              onClick={() => {
                onSuggestEdit({
                  content: disclosure.node.content,
                  currentVersion: disclosure.node.currentVersion,
                  nodeId: disclosure.node.graphNodeId,
                  title: disclosure.node.title,
                });
              }}
              type="button"
            >
              Suggest edit
            </button>
          ) : null}
        </div>
      ) : null}
      <button
        onClick={() => {
          const nextViewport = {
            target: initialViewport.target,
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM,
          };

          onViewportFrameChange?.(nextViewport);
          onViewportChange(nextViewport);
        }}
        type="button"
      >
        Zoom in
      </button>
      <button
        onClick={() => {
          const nextViewport = {
            target: initialViewport.target,
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM - 0.1,
          };

          onViewportFrameChange?.(nextViewport);
          onViewportChange(nextViewport);
        }}
        type="button"
      >
        Zoom out
      </button>
      <button
        onClick={() =>
          onViewportFrameChange?.({
            target: [
              initialViewport.target[0] + 40,
              initialViewport.target[1] + 30,
              0,
            ],
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM,
          })
        }
        type="button"
      >
        Frame move
      </button>
      <button
        onClick={() =>
          onViewportFrameChange?.({
            target: initialViewport.target,
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM,
          })
        }
        type="button"
      >
        Live zoom in
      </button>
      <button
        onClick={() =>
          onViewportFrameChange?.({
            target: initialViewport.target,
            zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM - 0.1,
          })
        }
        type="button"
      >
        Live zoom out
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
  TaxonomyCardScopeLayoutSliceResponse,
  TaxonomyCardScopeNodeDetailsResponse,
  TaxonomyCardScopeNodeTitlesResponse,
  TaxonomyLeafView,
} from "../../data/taxonomyViewQueries";
import * as taxonomyViewQueries from "../../data/taxonomyViewQueries";
import { LeafRenderer } from "./LeafRenderer";

const mockUseTaxonomyCardScopeLayoutSliceQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyCardScopeLayoutSliceQuery,
);
const mockUseTaxonomyCardScopeNodeDetailsQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyCardScopeNodeDetailsQuery,
);
const mockUseTaxonomyCardScopeNodeTitlesQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyCardScopeNodeTitlesQuery,
);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function makeLeafView(): TaxonomyLeafView {
  return {
    breadcrumb: [],
    current_scope: {
      depth: 2,
      name: "Algebra",
      parent_taxonomy_node_id: 1,
      route_path: "math/algebra",
      route_slug: "algebra",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 2,
    },
    edge_count: 1,
    generated_at: "2026-04-29T00:00:00Z",
    layout_version: "taxonomy-card-scope-layout-v1",
    layout_status: "ready",
    node_kind: "card_scope",
    node_count: 2,
    world_bounds: { max_x: 44, max_y: 34, min_x: -44, min_y: -34 },
  };
}

function makeLeafLayoutSliceResponse(): TaxonomyCardScopeLayoutSliceResponse {
  return {
    edges: [[10, 11, 0.8]],
    layout_version: "taxonomy-card-scope-layout-v1",
    layout_status: "ready",
    nodes: [
      { id: 10, scope: "inner", x: 0, y: 0 },
      { id: 11, scope: "outer", x: 40, y: 30 },
    ],
    route_path: "math/algebra",
    scope_kind: "taxonomy_node",
    taxonomy_node_id: 2,
    requested_bounds: {
      max_x: 2048,
      max_y: 2048,
      min_x: -2048,
      min_y: -2048,
    },
  };
}

function makeLeafTitlesResponse(): TaxonomyCardScopeNodeTitlesResponse {
  return {
    nodes: [
      { id: 10, title: "Equation \\(E=mc^2\\)" },
      { id: 11, title: "Proof" },
    ],
  };
}

function makeLeafDetailsResponse(
  nodeIds: readonly number[],
): TaxonomyCardScopeNodeDetailsResponse {
  const detailsById: Record<
    number,
    TaxonomyCardScopeNodeDetailsResponse["nodes"][number]
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
  mockUseTaxonomyCardScopeLayoutSliceQuery.mockImplementation(
    (_routePath, _bounds, _layoutIdentity, options) =>
      ({
        data: options.enabled ? makeLeafLayoutSliceResponse() : undefined,
        error: null,
        isError: false,
        isPending: false,
      }) as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyCardScopeLayoutSliceQuery
      >,
  );
  mockUseTaxonomyCardScopeNodeTitlesQuery.mockImplementation(
    (_routePath, _nodeIds, options) =>
      ({
        data: options.enabled ? makeLeafTitlesResponse() : undefined,
        error: null,
        isError: false,
        isPending: false,
      }) as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyCardScopeNodeTitlesQuery
      >,
  );
  mockUseTaxonomyCardScopeNodeDetailsQuery.mockImplementation(
    (_routePath, nodeIds, options) =>
      ({
        data: options.enabled ? makeLeafDetailsResponse(nodeIds) : undefined,
        error: null,
        isError: false,
        isPending: false,
      }) as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyCardScopeNodeDetailsQuery
      >,
  );
}

describe("LeafRenderer", () => {
  it("starts in point-title mode without detail hydration", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    expect(
      await screen.findByTestId("leaf-scene-point-count"),
    ).toHaveTextContent("2");
    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-scene-title-label-count"),
      ).toHaveTextContent("2");
    });
    expect(screen.getByTestId("leaf-scene-edge-count")).toHaveTextContent("1");
    expect(
      screen.getByTestId("leaf-point-interaction-enabled"),
    ).toHaveTextContent("true");
    expect(mockUseTaxonomyCardScopeLayoutSliceQuery).toHaveBeenCalledWith(
      "math/algebra",
      {
        max_x: 2048,
        max_y: 2048,
        min_x: -2048,
        min_y: -2048,
      },
      {
        generatedAt: "2026-04-29T00:00:00Z",
        layoutVersion: "taxonomy-card-scope-layout-v1",
      },
      expect.objectContaining({ enabled: true }),
    );
    expect(
      screen.getByTestId("leaf-scene-first-point-radius"),
    ).toHaveTextContent("8");
    await waitFor(() => {
      expect(mockUseTaxonomyCardScopeNodeTitlesQuery).toHaveBeenCalledWith(
        "math/algebra",
        expect.arrayContaining([10, 11]),
        expect.objectContaining({ enabled: true }),
      );
    });
    expect(mockUseTaxonomyCardScopeNodeDetailsQuery).toHaveBeenCalledWith(
      "math/algebra",
      [],
      expect.objectContaining({ enabled: false }),
    );
  });

  it("starts the initial viewport just above the title threshold for large leaf bounds", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        leafView={{
          ...makeLeafView(),
          world_bounds: {
            max_x: 1400,
            max_y: 500,
            min_x: -1400,
            min_y: -500,
          },
        }}
        viewport={{ height: 800, width: 1200 }}
      />,
    );

    const initialZoom = Number(
      (await screen.findByTestId("leaf-initial-viewport-zoom")).textContent,
    );

    expect(initialZoom).toBeGreaterThan(LEAF_POINT_TITLE_ACTIVATION_ZOOM);
    expect(initialZoom).toBeCloseTo(LEAF_POINT_TITLE_ACTIVATION_ZOOM + 0.01);
    expect(mockUseTaxonomyCardScopeLayoutSliceQuery).toHaveBeenCalledWith(
      "math/algebra",
      {
        max_x: expect.any(Number),
        max_y: expect.any(Number),
        min_x: expect.any(Number),
        min_y: expect.any(Number),
      },
      {
        generatedAt: "2026-04-29T00:00:00Z",
        layoutVersion: "taxonomy-card-scope-layout-v1",
      },
      expect.objectContaining({ enabled: true }),
    );
  });

  it("hydrates title labels at zoom 2 and moves the hovered title into the hover disclosure", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));

    await waitFor(() => {
      expect(mockUseTaxonomyCardScopeNodeTitlesQuery).toHaveBeenCalledWith(
        "math/algebra",
        expect.arrayContaining([10, 11]),
        expect.objectContaining({ enabled: true }),
      );
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-scene-title-label-count"),
      ).toHaveTextContent("2");
    });

    expect(
      screen.queryByTestId("taxonomy-leaf-title-label-10"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("leaf-hidden-label-node-id")).toHaveTextContent(
      "none",
    );

    fireEvent.click(screen.getByRole("button", { name: "Hover 10" }));

    await waitFor(() => {
      expect(mockUseTaxonomyCardScopeNodeDetailsQuery).toHaveBeenCalledWith(
        "math/algebra",
        [10],
        expect.objectContaining({ enabled: true }),
      );
    });

    const disclosure = await screen.findByTestId(
      "taxonomy-leaf-disclosure-overlay",
    );

    expect(disclosure.parentElement).toBe(
      screen.getByTestId("leaf-deck-scene-mock"),
    );
    expect(disclosure).toHaveAttribute("data-disclosure-mode", "hover");
    expect(disclosure).toHaveTextContent("Equation");
    expect(disclosure).toHaveTextContent("Equation content");
    expect(screen.getByTestId("leaf-active-focus-node-id")).toHaveTextContent(
      "10",
    );
    expect(screen.getByTestId("leaf-hidden-label-node-id")).toHaveTextContent(
      "10",
    );
  });

  it("shows selected disclosure with title, hides that label, and toggles selection from the point", async () => {
    installSuccessfulQueryMocks();
    const onSuggestEdit = vi.fn();

    render(
      <LeafRenderer
        leafView={makeLeafView()}
        onSuggestEdit={onSuggestEdit}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));
    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-scene-title-label-count"),
      ).toHaveTextContent("2");
    });

    fireEvent.click(screen.getByRole("button", { name: "Click 10" }));

    const selectedDisclosure = await screen.findByTestId(
      "taxonomy-leaf-disclosure-overlay",
    );

    expect(selectedDisclosure.parentElement).toBe(
      screen.getByTestId("leaf-deck-scene-mock"),
    );
    expect(selectedDisclosure).toHaveAttribute(
      "data-disclosure-mode",
      "selected",
    );
    expect(selectedDisclosure).toHaveTextContent("Equation");
    expect(selectedDisclosure).toHaveTextContent("Equation content");
    expect(screen.getByTestId("leaf-hidden-label-node-id")).toHaveTextContent(
      "10",
    );

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
    expect(screen.getByTestId("leaf-hidden-label-node-id")).toHaveTextContent(
      "none",
    );
  });

  it("keeps selected as the graph focus while another point is hovered, then falls back to hover after clearing selected", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));
    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-scene-title-label-count"),
      ).toHaveTextContent("2");
    });

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
    expect(screen.getByTestId("leaf-hidden-label-node-id")).toHaveTextContent(
      "10",
    );

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
    expect(screen.getByTestId("leaf-hidden-label-node-id")).toHaveTextContent(
      "11",
    );
  });

  it("clears hover and selected state when returning below the title zoom", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zoom in" }));
    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-scene-title-label-count"),
      ).toHaveTextContent("2");
    });
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
    expect(screen.getByTestId("leaf-hidden-label-node-id")).toHaveTextContent(
      "none",
    );
  });

  it("toggles point-title mode from live deck zoom frames without waiting for a viewport snapshot", async () => {
    installSuccessfulQueryMocks();

    render(
      <LeafRenderer
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    expect(
      await screen.findByTestId("leaf-point-interaction-enabled"),
    ).toHaveTextContent("true");

    fireEvent.click(screen.getByRole("button", { name: "Click 10" }));

    await screen.findByTestId("taxonomy-leaf-disclosure-overlay");

    fireEvent.click(screen.getByRole("button", { name: "Live zoom out" }));

    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-point-interaction-enabled"),
      ).toHaveTextContent("false");
    });
    expect(
      screen.queryByTestId("taxonomy-leaf-disclosure-overlay"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Live zoom in" }));

    await waitFor(() => {
      expect(
        screen.getByTestId("leaf-point-interaction-enabled"),
      ).toHaveTextContent("true");
    });
  });
});
