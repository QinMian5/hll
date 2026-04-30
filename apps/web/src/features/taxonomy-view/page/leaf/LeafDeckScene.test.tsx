// abstract: Contract tests for taxonomy leaf deck.gl scene layer assembly.
// out_of_scope: Real WebGL rendering and leaf data hydration.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LeafDeckScene } from "./LeafDeckScene";
import type { LeafSceneModel, LeafSceneTitleLabelNode } from "./leafSceneTypes";

const layerTestState = vi.hoisted(() => ({
  createdLayers: [] as Array<{
    readonly props: Record<string, unknown>;
    readonly type: string;
  }>,
}));

vi.mock("@deck.gl/core", () => ({
  OrthographicView: class OrthographicView {
    readonly props: unknown;

    constructor(props: unknown) {
      this.props = props;
    }
  },
}));

vi.mock("@deck.gl/layers", () => {
  class MockLayer {
    readonly props: Record<string, unknown>;

    constructor(props: Record<string, unknown>) {
      this.props = props;
      layerTestState.createdLayers.push({
        props,
        type: this.constructor.name,
      });
    }
  }

  return {
    LineLayer: class LineLayer extends MockLayer {},
    ScatterplotLayer: class ScatterplotLayer extends MockLayer {},
    TextLayer: class TextLayer extends MockLayer {},
  };
});

vi.mock("@deck.gl/react", () => ({
  DeckGL: ({ layers }: { readonly layers: readonly unknown[] }) => (
    <div data-layer-count={layers.length} data-testid="deck-gl-mock" />
  ),
}));

afterEach(() => {
  cleanup();
  layerTestState.createdLayers.length = 0;
});

function makeScene(): LeafSceneModel {
  return {
    bounds: { bottom: 96, left: -96, right: 96, top: -96 },
    edgeIdsByNodeId: new Map(),
    edges: [],
    focusNodeIdsByNodeId: new Map(),
    highlightEdgesByNodeId: new Map(),
    neighborNodeIdsByNodeId: new Map(),
    pointNodes: [
      {
        graphNodeId: 10,
        id: "leaf-10",
        position: { x: 10, y: 20 },
        radius: 4,
        scope: "inner",
      },
      {
        graphNodeId: 11,
        id: "leaf-11",
        position: { x: 30, y: 40 },
        radius: 4,
        scope: "outer",
      },
    ],
    titleLabelNodes: [
      {
        graphNodeId: 10,
        id: "leaf-10",
        position: { x: 10, y: 20 },
        scope: "inner",
        title: "Visible title",
      },
      {
        graphNodeId: 11,
        id: "leaf-11",
        position: { x: 30, y: 40 },
        scope: "outer",
        title: "Hidden title",
      },
    ],
  };
}

function renderScene(hiddenLabelNodeId: number | null) {
  render(
    <LeafDeckScene
      activeFocusNodeId={null}
      hiddenLabelNodeId={hiddenLabelNodeId}
      hoveredPointNodeId={null}
      initialViewport={{ target: [0, 0, 0], zoom: 0 }}
      isPointInteractionEnabled={true}
      onCanvasClick={vi.fn()}
      onPointClick={vi.fn()}
      onPointHover={vi.fn()}
      onViewportChange={vi.fn()}
      scene={makeScene()}
    />,
  );
}

describe("LeafDeckScene", () => {
  it("renders visible title labels through a non-pickable deck.gl TextLayer", () => {
    renderScene(11);

    expect(screen.getByTestId("deck-gl-mock")).toHaveAttribute(
      "data-layer-count",
      "5",
    );

    const titleLayer = layerTestState.createdLayers.find(
      (layer) => layer.type === "TextLayer",
    );

    expect(titleLayer).toBeDefined();
    expect(titleLayer?.props.id).toBe("taxonomy-leaf-title-labels");
    expect(titleLayer?.props.pickable).toBe(false);
    expect(titleLayer?.props.getPixelOffset).toEqual([0, 8]);
    expect(titleLayer?.props.getTextAnchor).toBe("middle");
    expect(titleLayer?.props.getAlignmentBaseline).toBe("top");

    const labels = titleLayer?.props.data as readonly LeafSceneTitleLabelNode[];

    expect(labels.map((label) => label.graphNodeId)).toEqual([10]);
    expect(
      (titleLayer?.props.getText as (label: LeafSceneTitleLabelNode) => string)(
        labels[0],
      ),
    ).toBe("Visible title");
    expect(
      (
        titleLayer?.props.getPosition as (
          label: LeafSceneTitleLabelNode,
        ) => readonly [number, number]
      )(labels[0]),
    ).toEqual([10, 20]);
  });
});
