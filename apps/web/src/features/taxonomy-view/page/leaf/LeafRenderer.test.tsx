// abstract: Behavior tests for leaf renderer hydration, scene shaping, and hover disclosure.
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

import { LEAF_CARD_ACTIVATION_ZOOM } from "./leafRendererConfig";

vi.mock("../../data/taxonomyViewQueries", () => ({
  useTaxonomyLeafNodeDetailsQuery: vi.fn(),
}));

vi.mock("./LeafDeckScene", () => ({
  LeafDeckScene: ({
    hoveredNodeId,
    onViewportChange,
    scene,
  }: {
    readonly hoveredNodeId: number | null;
    readonly onViewportChange: (viewport: {
      readonly target: readonly [number, number, number];
      readonly zoom: number;
    }) => void;
    readonly scene: {
      readonly cardNodes: ReadonlyArray<{
        readonly content?: string;
        readonly label: string;
      }>;
      readonly edges: ReadonlyArray<unknown>;
      readonly pointNodes: ReadonlyArray<unknown>;
    };
  }) => (
    <div data-testid="leaf-deck-scene-mock">
      <div data-testid="leaf-hovered-node-id">{hoveredNodeId ?? "none"}</div>
      <div data-testid="leaf-scene-point-count">{scene.pointNodes.length}</div>
      <div data-testid="leaf-scene-card-count">{scene.cardNodes.length}</div>
      <div data-testid="leaf-scene-edge-count">{scene.edges.length}</div>
      <button
        onClick={() =>
          onViewportChange({
            target: [700, 450, 0],
            zoom: LEAF_CARD_ACTIVATION_ZOOM,
          })
        }
        type="button"
      >
        Zoom in
      </button>
    </div>
  ),
}));

import type {
  TaxonomyLeafNodeDetailsResponse,
  TaxonomyLeafView,
} from "../../data/taxonomyViewQueries";
import * as taxonomyViewQueries from "../../data/taxonomyViewQueries";
import { LeafRenderer } from "./LeafRenderer";

const mockUseTaxonomyLeafNodeDetailsQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyLeafNodeDetailsQuery,
);

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

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
    edges: [[10, 11, 0.8]],
    node_kind: "leaf",
    nodes: [
      { id: 10, scope: "inner" },
      { id: 11, scope: "outer" },
    ],
  };
}

function makeLeafDetailsResponse(): TaxonomyLeafNodeDetailsResponse {
  return {
    nodes: [
      {
        content: "*Equation* content",
        id: 10,
        title: "Equation \\(E=mc^2\\)",
      },
      { content: "Proof content", id: 11, title: "Proof" },
    ],
  };
}

describe("LeafRenderer", () => {
  it("renders points and edges before the activation zoom without hydrating cards", () => {
    mockUseTaxonomyLeafNodeDetailsQuery.mockReturnValue({
      data: undefined,
      error: null,
      isError: false,
      isPending: false,
    } as unknown as ReturnType<
      typeof taxonomyViewQueries.useTaxonomyLeafNodeDetailsQuery
    >);

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    expect(screen.getByTestId("leaf-scene-point-count")).toHaveTextContent("2");
    expect(screen.getByTestId("leaf-scene-card-count")).toHaveTextContent("0");
    expect(screen.getByTestId("leaf-scene-edge-count")).toHaveTextContent("1");
    expect(mockUseTaxonomyLeafNodeDetailsQuery).toHaveBeenCalledWith(
      2,
      [],
      expect.objectContaining({ enabled: false }),
    );
  });

  it("hydrates viewport-scoped cards into the DOM rich-text overlay and reveals hover disclosure", async () => {
    mockUseTaxonomyLeafNodeDetailsQuery.mockImplementation(
      (_leafId, _nodeIds, options) =>
        ({
          data: options.enabled ? makeLeafDetailsResponse() : undefined,
          error: null,
          isError: false,
          isPending: false,
        }) as unknown as ReturnType<
          typeof taxonomyViewQueries.useTaxonomyLeafNodeDetailsQuery
        >,
    );

    render(
      <LeafRenderer
        center={{ x: 700, y: 450 }}
        leafView={makeLeafView()}
        viewport={{ height: 900, width: 1404 }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));

    await waitFor(() => {
      expect(mockUseTaxonomyLeafNodeDetailsQuery).toHaveBeenCalledWith(
        2,
        expect.arrayContaining([10, 11]),
        expect.objectContaining({ enabled: true }),
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("leaf-scene-card-count")).toHaveTextContent(
        "2",
      );
    });
    expect(
      screen.getByTestId("taxonomy-leaf-rich-text-cards-overlay"),
    ).toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();

    const firstCard = screen.getByTestId("taxonomy-leaf-rich-text-card-10");

    fireEvent.focus(firstCard);

    const hoverOverlay = screen.getByTestId("taxonomy-leaf-hover-overlay");
    const cardLeft = Number.parseFloat(firstCard.style.left);
    const cardTop = Number.parseFloat(firstCard.style.top);
    const overlayLeft = Number.parseFloat(hoverOverlay.style.left);
    const overlayTop = Number.parseFloat(hoverOverlay.style.top);

    expect(hoverOverlay).toHaveTextContent("Equation content");
    expect(screen.getByTestId("leaf-hovered-node-id")).toHaveTextContent("10");
    expect(overlayLeft).toBeCloseTo(cardLeft, 4);
    expect(overlayTop).toBeGreaterThan(cardTop);
    expect(hoverOverlay).toHaveStyle({ transform: "translateX(-50%)" });
  });
});
