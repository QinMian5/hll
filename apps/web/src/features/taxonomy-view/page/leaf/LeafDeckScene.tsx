// abstract: deck.gl scene assembly for taxonomy leaf point, edge, and title-label rendering.
// out_of_scope: Taxonomy data fetching and page-shell overlays.

import { OrthographicView } from "@deck.gl/core";
import { LineLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { DeckGL } from "@deck.gl/react";
import { useCallback, useMemo } from "react";

import type { SearchResultCardEditPayload } from "../../../search/components/SearchResultCard";
import { LeafDisclosureOverlay } from "./LeafDisclosureOverlay";
import { LeafZoomControl } from "./LeafZoomControl.tsx";
import {
  LEAF_EDGE_ACTIVE_OPACITY,
  LEAF_EDGE_BASE_OPACITY,
  LEAF_EDGE_DIMMED_OPACITY,
  LEAF_POINT_COLOR_RGB,
  LEAF_POINT_DIMMED_OPACITY,
  LEAF_POINT_HOVER_OPACITY,
  LEAF_POINT_INNER_OPACITY,
  LEAF_POINT_OUTER_OPACITY,
  LEAF_TITLE_LABEL_BASE_ALPHA,
  LEAF_TITLE_LABEL_FONT_SIZE_PX,
  LEAF_TITLE_LABEL_LINE_HEIGHT,
  LEAF_TITLE_LABEL_MAX_WIDTH_EM,
  LEAF_TITLE_LABEL_PIXEL_OFFSET_Y,
} from "./leafRendererConfig";
import type {
  LeafDisclosureState,
  LeafOrthographicViewport,
  LeafSceneEdge,
  LeafSceneModel,
  LeafScenePointNode,
  LeafSceneTitleLabelNode,
} from "./leafSceneTypes";
import {
  deckZoomToLeafZoomPercent,
  leafZoomPercentToDeckZoom,
} from "./leafZoomControl";
import { leafPointTitleOpacity } from "./useLeafViewportController";
import { useLeafViewportStore } from "./useLeafViewportStore";

interface LeafDeckSceneProps {
  readonly activeFocusNodeId: number | null;
  readonly disclosure: LeafDisclosureState | null;
  readonly hiddenLabelNodeId: number | null;
  readonly hoveredPointNodeId: number | null;
  readonly initialViewport: LeafOrthographicViewport;
  readonly isPointInteractionEnabled: boolean;
  readonly onCanvasClick: () => void;
  readonly onPointClick: (nodeId: number) => void;
  readonly onPointHover: (nodeId: number | null) => void;
  readonly onSuggestEdit?: (card: SearchResultCardEditPayload) => void;
  readonly onViewportFrameChange?: (viewport: LeafOrthographicViewport) => void;
  readonly onViewportChange: (viewport: LeafOrthographicViewport) => void;
  readonly scene: LeafSceneModel;
}

interface DeckLeafViewState {
  readonly target?: readonly number[];
  readonly zoom?: number | readonly number[];
}

const TITLE_LABEL_FONT_SETTINGS = {
  buffer: 16,
  cutoff: 0.25,
  fontSize: 256,
  radius: 24,
  sdf: true,
  smoothing: 0.1,
} as const;

const leafView = new OrthographicView({
  controller: true,
  flipY: true,
  id: "taxonomy-leaf-view",
});

function toLeafViewport(
  viewState: DeckLeafViewState,
  fallbackViewport: LeafOrthographicViewport,
): LeafOrthographicViewport {
  const target = viewState.target ?? fallbackViewport.target;
  const nextZoom = Array.isArray(viewState.zoom)
    ? (viewState.zoom[0] ?? fallbackViewport.zoom)
    : (viewState.zoom ?? fallbackViewport.zoom);

  return {
    target: [
      target[0] ?? fallbackViewport.target[0],
      target[1] ?? fallbackViewport.target[1],
      target[2] ?? 0,
    ],
    zoom: nextZoom,
  };
}

export function LeafDeckScene({
  activeFocusNodeId,
  disclosure,
  hiddenLabelNodeId,
  hoveredPointNodeId,
  onViewportFrameChange,
  onViewportChange,
  isPointInteractionEnabled,
  initialViewport,
  onCanvasClick,
  onPointClick,
  onPointHover,
  onSuggestEdit,
  scene,
}: LeafDeckSceneProps) {
  const { publishViewport, viewState } = useLeafViewportStore({
    initialViewport,
    onViewportSnapshotChange: onViewportChange,
  });
  const zoomPercent = deckZoomToLeafZoomPercent(viewState.zoom);
  const titleLabelOpacity = leafPointTitleOpacity(viewState.zoom);
  const titleLabelAlpha = Math.round(
    LEAF_TITLE_LABEL_BASE_ALPHA * titleLabelOpacity,
  );
  const publishZoomPercent = useCallback(
    (percent: number) => {
      const nextViewport = {
        target: viewState.target,
        zoom: leafZoomPercentToDeckZoom(percent),
      };

      onViewportFrameChange?.(nextViewport);
      publishViewport(nextViewport);
    },
    [onViewportFrameChange, publishViewport, viewState.target],
  );
  const highlightedEdges = useMemo(
    () =>
      activeFocusNodeId
        ? (scene.highlightEdgesByNodeId.get(activeFocusNodeId) ?? [])
        : [],
    [activeFocusNodeId, scene.highlightEdgesByNodeId],
  );
  const focusNodeIds = useMemo(
    () =>
      activeFocusNodeId
        ? (scene.focusNodeIdsByNodeId.get(activeFocusNodeId) ?? null)
        : null,
    [activeFocusNodeId, scene.focusNodeIdsByNodeId],
  );
  const focusHaloNodes = useMemo(
    () =>
      focusNodeIds
        ? scene.pointNodes.filter((node) => focusNodeIds.has(node.graphNodeId))
        : [],
    [focusNodeIds, scene.pointNodes],
  );
  const visibleTitleLabelNodes = useMemo(() => {
    if (titleLabelOpacity <= 0) {
      return [];
    }

    return hiddenLabelNodeId === null
      ? scene.titleLabelNodes
      : scene.titleLabelNodes.filter(
          (node) => node.graphNodeId !== hiddenLabelNodeId,
        );
  }, [hiddenLabelNodeId, scene.titleLabelNodes, titleLabelOpacity]);
  const layers = useMemo(
    () => [
      new LineLayer<LeafSceneEdge>({
        data: scene.edges,
        getColor: activeFocusNodeId
          ? [120, 163, 243, Math.round(255 * LEAF_EDGE_DIMMED_OPACITY)]
          : [120, 163, 243, Math.round(255 * LEAF_EDGE_BASE_OPACITY)],
        getSourcePosition: (edge) => [edge.source.x, edge.source.y],
        getTargetPosition: (edge) => [edge.target.x, edge.target.y],
        getWidth: () => 1,
        id: "taxonomy-leaf-edges",
        pickable: false,
        widthUnits: "pixels",
      }),
      new LineLayer<LeafSceneEdge>({
        data: highlightedEdges,
        getColor: [120, 163, 243, Math.round(255 * LEAF_EDGE_ACTIVE_OPACITY)],
        getSourcePosition: (edge) => [edge.source.x, edge.source.y],
        getTargetPosition: (edge) => [edge.target.x, edge.target.y],
        getWidth: () => 2,
        id: "taxonomy-leaf-highlight-edges",
        pickable: false,
        widthUnits: "pixels",
      }),
      new ScatterplotLayer<LeafScenePointNode>({
        data: focusHaloNodes,
        filled: true,
        getFillColor: (node) => [
          LEAF_POINT_COLOR_RGB[0],
          LEAF_POINT_COLOR_RGB[1],
          LEAF_POINT_COLOR_RGB[2],
          node.graphNodeId === activeFocusNodeId ? 48 : 34,
        ],
        getPosition: (node) => [node.position.x, node.position.y],
        getRadius: (node) => (node.graphNodeId === activeFocusNodeId ? 32 : 24),
        id: "taxonomy-leaf-focus-halos",
        pickable: false,
        radiusUnits: "common",
        stroked: false,
      }),
      new ScatterplotLayer<LeafScenePointNode>({
        data: scene.pointNodes,
        filled: true,
        getFillColor: (node) => {
          const baseOpacity =
            node.scope === "inner"
              ? LEAF_POINT_INNER_OPACITY
              : LEAF_POINT_OUTER_OPACITY;
          const opacity = focusNodeIds
            ? Math.max(
                focusNodeIds.has(node.graphNodeId)
                  ? baseOpacity
                  : LEAF_POINT_DIMMED_OPACITY,
                node.graphNodeId === hoveredPointNodeId ? 0.46 : 0,
              )
            : node.graphNodeId === hoveredPointNodeId
              ? LEAF_POINT_HOVER_OPACITY
              : baseOpacity;

          return [
            LEAF_POINT_COLOR_RGB[0],
            LEAF_POINT_COLOR_RGB[1],
            LEAF_POINT_COLOR_RGB[2],
            Math.round(255 * opacity),
          ];
        },
        getPosition: (node) => [node.position.x, node.position.y],
        getRadius: (node) => node.radius,
        id: "taxonomy-leaf-points",
        onClick: (info) => {
          const node = info.object;
          if (!node) {
            return false;
          }

          onPointClick(node.graphNodeId);
          return true;
        },
        onHover: (info) => {
          const node = info.object;
          onPointHover(node?.graphNodeId ?? null);
        },
        pickable: isPointInteractionEnabled,
        radiusMinPixels: 2,
        radiusUnits: "common",
        stroked: false,
      }),
      new TextLayer<LeafSceneTitleLabelNode>({
        billboard: true,
        characterSet: "auto",
        data: visibleTitleLabelNodes,
        fontFamily: '"Geist", sans-serif',
        fontSettings: TITLE_LABEL_FONT_SETTINGS,
        fontWeight: "500",
        getAlignmentBaseline: "top",
        getColor: [38, 52, 77, titleLabelAlpha],
        getPixelOffset: [0, LEAF_TITLE_LABEL_PIXEL_OFFSET_Y],
        getPosition: (label) => [label.position.x, label.position.y],
        getSize: LEAF_TITLE_LABEL_FONT_SIZE_PX,
        getText: (label) => label.title,
        getTextAnchor: "middle",
        id: "taxonomy-leaf-title-labels",
        lineHeight: LEAF_TITLE_LABEL_LINE_HEIGHT,
        maxWidth: LEAF_TITLE_LABEL_MAX_WIDTH_EM,
        pickable: false,
        sizeUnits: "pixels",
        wordBreak: "break-word",
      }),
    ],
    [
      activeFocusNodeId,
      focusHaloNodes,
      focusNodeIds,
      highlightedEdges,
      hoveredPointNodeId,
      isPointInteractionEnabled,
      onPointClick,
      onPointHover,
      scene.edges,
      scene.pointNodes,
      titleLabelAlpha,
      visibleTitleLabelNodes,
    ],
  );

  return (
    <div className="absolute inset-0" data-testid="taxonomy-leaf-renderer">
      <DeckGL
        layers={layers}
        onClick={(info) => {
          if (!info.object) {
            onCanvasClick();
          }
        }}
        onViewStateChange={({ viewState }) => {
          const nextViewport = toLeafViewport(viewState, initialViewport);

          onViewportFrameChange?.(nextViewport);
          publishViewport(nextViewport);
        }}
        viewState={{ target: [...viewState.target], zoom: viewState.zoom }}
        views={leafView}
      >
        {({
          height,
          viewState,
          width,
        }: {
          readonly height: number;
          readonly viewState: DeckLeafViewState;
          readonly width: number;
        }) => (
          <LeafDisclosureOverlay
            canvas={{ height, width }}
            disclosure={disclosure}
            onSuggestEdit={onSuggestEdit}
            viewport={toLeafViewport(viewState, initialViewport)}
          />
        )}
      </DeckGL>
      <LeafZoomControl
        onZoomPercentChange={publishZoomPercent}
        onZoomPercentCommit={publishZoomPercent}
        zoomPercent={zoomPercent}
      />
    </div>
  );
}
