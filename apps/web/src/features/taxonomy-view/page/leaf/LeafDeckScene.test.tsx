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
  DeckGL: ({
    children,
    layers,
    viewState,
  }: {
    readonly children?: unknown;
    readonly layers: readonly unknown[];
    readonly viewState: {
      readonly target: readonly [number, number, number];
      readonly zoom: number;
    };
  }) => (
    <div data-layer-count={layers.length} data-testid="deck-gl-mock">
      {typeof children === "function"
        ? children({
            height: 480,
            viewState,
            viewport: {},
            width: 640,
            x: 0,
            y: 0,
          })
        : children}
    </div>
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
      disclosure={null}
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
    expect(titleLayer?.props.fontSettings).toEqual({
      buffer: 8,
      cutoff: 0.25,
      fontSize: 128,
      radius: 12,
      sdf: true,
      smoothing: 0.06,
    });
    expect(titleLayer?.props.getSize).toBe(12);
    expect(titleLayer?.props.getColor).toEqual([38, 52, 77, 232]);

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

  it("renders disclosure cards through the DeckGL child render callback", () => {
    render(
      <LeafDeckScene
        activeFocusNodeId={10}
        disclosure={{
          mode: "selected",
          node: {
            content: "*Visible* content",
            currentVersion: 3,
            graphNodeId: 10,
            id: "leaf-10",
            position: { x: 10, y: 20 },
            scope: "inner",
            title: "Visible title",
          },
        }}
        hiddenLabelNodeId={10}
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

    const disclosure = screen.getByTestId("taxonomy-leaf-disclosure-overlay");

    expect(disclosure.parentElement).toBe(screen.getByTestId("deck-gl-mock"));
    expect(disclosure).toHaveAttribute("data-disclosure-mode", "selected");
    expect(disclosure).toHaveTextContent("Visible title");
    expect(disclosure).toHaveTextContent("Visible content");
    expect(disclosure).toHaveStyle({
      transform: "translate3d(330px, 268px, 0px) translate(-50%, 0%)",
    });
  });
});
