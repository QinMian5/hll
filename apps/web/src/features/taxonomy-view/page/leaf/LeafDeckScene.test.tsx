// abstract: Contract tests for taxonomy leaf deck.gl scene layer assembly.
// out_of_scope: Real WebGL rendering and leaf data hydration.

import "@testing-library/jest-dom/vitest";

import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LeafDeckScene } from "./LeafDeckScene";
import {
  LEAF_POINT_TITLE_ACTIVATION_ZOOM,
  LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS,
} from "./leafRendererConfig";
import type {
  LeafOrthographicViewport,
  LeafSceneEdge,
  LeafSceneModel,
  LeafScenePointNode,
  LeafSceneTitleLabelNode,
} from "./leafSceneTypes";
import { leafZoomPercentToDeckZoom } from "./leafZoomControl";

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
    <div
      data-layer-count={layers.length}
      data-target={viewState.target.join(",")}
      data-testid="deck-gl-mock"
      data-zoom={viewState.zoom}
    >
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
  const edge: LeafSceneEdge = {
    id: "10:11",
    source: { x: 10, y: 20 },
    strength: 0.8,
    target: { x: 30, y: 40 },
  };

  return {
    bounds: { bottom: 96, left: -96, right: 96, top: -96 },
    edgeIdsByNodeId: new Map([
      [10, new Set(["10:11"])],
      [11, new Set(["10:11"])],
    ]),
    edges: [edge],
    focusNodeIdsByNodeId: new Map([[10, new Set([10, 11])]]),
    highlightEdgesByNodeId: new Map([[10, [edge]]]),
    neighborNodeIdsByNodeId: new Map([[10, new Set([11])]]),
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

function renderScene(options: {
  readonly activeFocusNodeId?: number | null;
  readonly initialViewport?: LeafOrthographicViewport;
  readonly hiddenLabelNodeId: number | null;
  readonly onViewportChange?: (viewport: LeafOrthographicViewport) => void;
  readonly onViewportFrameChange?: (viewport: LeafOrthographicViewport) => void;
}) {
  const onViewportChange = options.onViewportChange ?? vi.fn();
  const onViewportFrameChange = options.onViewportFrameChange ?? vi.fn();

  render(
    <LeafDeckScene
      activeFocusNodeId={options.activeFocusNodeId ?? null}
      disclosure={null}
      hiddenLabelNodeId={options.hiddenLabelNodeId}
      hoveredPointNodeId={null}
      initialViewport={
        options.initialViewport ?? { target: [0, 0, 0], zoom: 0 }
      }
      isPointInteractionEnabled={true}
      onCanvasClick={vi.fn()}
      onPointClick={vi.fn()}
      onPointHover={vi.fn()}
      onViewportChange={onViewportChange}
      onViewportFrameChange={onViewportFrameChange}
      scene={makeScene()}
    />,
  );

  return { onViewportChange, onViewportFrameChange };
}

function findLayer(id: string) {
  return layerTestState.createdLayers.find((layer) => layer.props.id === id);
}

describe("LeafDeckScene", () => {
  it("renders the leaf zoom control as a screen-fixed scene overlay", () => {
    renderScene({ hiddenLabelNodeId: null });

    expect(screen.getByTestId("leaf-zoom-control")).toBeInTheDocument();
    expect(
      screen.getByRole("slider", { name: "Leaf zoom" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("leaf-zoom-control").parentElement).toBe(
      screen.getByTestId("taxonomy-leaf-renderer"),
    );
  });

  it("publishes slider zoom changes through live frame and snapshot viewport paths", () => {
    vi.useFakeTimers();
    const onViewportChange = vi.fn();
    const onViewportFrameChange = vi.fn();
    const target = [12, 24, 0] as const;
    const expectedViewport = {
      target,
      zoom: leafZoomPercentToDeckZoom(200),
    };

    renderScene({
      hiddenLabelNodeId: null,
      initialViewport: {
        target,
        zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM,
      },
      onViewportChange,
      onViewportFrameChange,
    });
    onViewportChange.mockClear();

    fireEvent.change(screen.getByRole("slider", { name: "Leaf zoom" }), {
      target: { value: "1" },
    });

    expect(onViewportFrameChange).toHaveBeenLastCalledWith(expectedViewport);
    expect(screen.getByTestId("deck-gl-mock")).toHaveAttribute(
      "data-zoom",
      String(expectedViewport.zoom),
    );

    act(() => {
      vi.advanceTimersByTime(LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS);
    });

    expect(onViewportChange).toHaveBeenLastCalledWith(expectedViewport);
    vi.useRealTimers();
  });

  it("steps plus and minus without changing the current deck target", () => {
    const onViewportFrameChange = vi.fn();
    const target = [18, 36, 0] as const;

    renderScene({
      hiddenLabelNodeId: null,
      initialViewport: {
        target,
        zoom: LEAF_POINT_TITLE_ACTIVATION_ZOOM,
      },
      onViewportFrameChange,
    });

    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(onViewportFrameChange).toHaveBeenLastCalledWith({
      target,
      zoom: leafZoomPercentToDeckZoom(200),
    });
    expect(screen.getByTestId("deck-gl-mock")).toHaveAttribute(
      "data-target",
      "18,36,0",
    );

    fireEvent.click(screen.getByRole("button", { name: "Zoom out" }));
    expect(onViewportFrameChange).toHaveBeenLastCalledWith({
      target,
      zoom: leafZoomPercentToDeckZoom(100),
    });
    expect(screen.getByTestId("deck-gl-mock")).toHaveAttribute(
      "data-target",
      "18,36,0",
    );
  });

  it("renders visible title labels through a non-pickable deck.gl TextLayer", () => {
    renderScene({ hiddenLabelNodeId: 11 });

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
    expect(titleLayer?.props.getPixelOffset).toEqual([0, 16]);
    expect(titleLayer?.props.getTextAnchor).toBe("middle");
    expect(titleLayer?.props.getAlignmentBaseline).toBe("top");
    expect(titleLayer?.props.fontSettings).toEqual({
      buffer: 16,
      cutoff: 0.25,
      fontSize: 256,
      radius: 24,
      sdf: true,
      smoothing: 0.1,
    });
    expect(titleLayer?.props.getSize).toBe(24);
    expect(titleLayer?.props.maxWidth).toBe(16);
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

  it("uses world-sized points with fixed-width pixel edges", () => {
    renderScene({ activeFocusNodeId: 10, hiddenLabelNodeId: null });

    const edgeLayer = findLayer("taxonomy-leaf-edges");
    const highlightEdgeLayer = findLayer("taxonomy-leaf-highlight-edges");
    const focusHaloLayer = findLayer("taxonomy-leaf-focus-halos");
    const pointLayer = findLayer("taxonomy-leaf-points");

    expect(edgeLayer?.props.getWidth).toBeTypeOf("function");
    expect((edgeLayer?.props.getWidth as () => number)()).toBe(1);
    expect(edgeLayer?.props.widthUnits).toBe("pixels");
    expect(highlightEdgeLayer?.props.getWidth).toBeTypeOf("function");
    expect((highlightEdgeLayer?.props.getWidth as () => number)()).toBe(2);
    expect(highlightEdgeLayer?.props.widthUnits).toBe("pixels");
    expect(pointLayer?.props.stroked).toBe(false);
    expect(pointLayer?.props.radiusUnits).toBe("common");
    expect(focusHaloLayer?.props.radiusUnits).toBe("common");

    const haloNodes = focusHaloLayer?.props.data as
      | readonly LeafScenePointNode[]
      | undefined;
    const activeHaloNode = haloNodes?.find((node) => node.graphNodeId === 10);
    const neighborHaloNode = haloNodes?.find((node) => node.graphNodeId === 11);
    const getRadius = focusHaloLayer?.props.getRadius as
      | ((node: LeafScenePointNode) => number)
      | undefined;

    expect(getRadius).toBeTypeOf("function");
    expect(getRadius?.(activeHaloNode as LeafScenePointNode)).toBe(32);
    expect(getRadius?.(neighborHaloNode as LeafScenePointNode)).toBe(24);
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
