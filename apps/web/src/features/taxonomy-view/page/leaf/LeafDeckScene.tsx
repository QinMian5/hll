// abstract: deck.gl scene assembly for taxonomy leaf point and edge rendering.
// out_of_scope: Taxonomy data fetching and page-shell overlays.

import { OrthographicView } from "@deck.gl/core";
import { LineLayer, ScatterplotLayer } from "@deck.gl/layers";
import { DeckGL } from "@deck.gl/react";
import { useMemo } from "react";

import {
  LEAF_EDGE_ACTIVE_OPACITY,
  LEAF_EDGE_BASE_OPACITY,
  LEAF_EDGE_DIMMED_OPACITY,
  LEAF_POINT_COLOR_RGB,
  LEAF_POINT_DIMMED_OPACITY,
  LEAF_POINT_HOVER_OPACITY,
  LEAF_POINT_INNER_OPACITY,
  LEAF_POINT_OUTER_OPACITY,
} from "./leafRendererConfig";
import type {
  LeafOrthographicViewport,
  LeafSceneEdge,
  LeafSceneModel,
  LeafScenePointNode,
} from "./leafSceneTypes";
import { useLeafViewportStore } from "./useLeafViewportStore";

interface LeafDeckSceneProps {
  readonly activeFocusNodeId: number | null;
  readonly hoveredPointNodeId: number | null;
  readonly initialViewport: LeafOrthographicViewport;
  readonly isPointInteractionEnabled: boolean;
  readonly onCanvasClick: () => void;
  readonly onPointClick: (nodeId: number) => void;
  readonly onPointHover: (nodeId: number | null) => void;
  readonly onViewportFrameChange?: (viewport: LeafOrthographicViewport) => void;
  readonly onViewportChange: (viewport: LeafOrthographicViewport) => void;
  readonly scene: LeafSceneModel;
}

const leafView = new OrthographicView({
  controller: true,
  flipY: true,
  id: "taxonomy-leaf-view",
});

export function LeafDeckScene({
  activeFocusNodeId,
  hoveredPointNodeId,
  onViewportFrameChange,
  onViewportChange,
  isPointInteractionEnabled,
  initialViewport,
  onCanvasClick,
  onPointClick,
  onPointHover,
  scene,
}: LeafDeckSceneProps) {
  const { publishViewport, viewState } = useLeafViewportStore({
    initialViewport,
    onViewportSnapshotChange: onViewportChange,
  });
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
        getWidth: () => 1.5,
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
        getRadius: (node) => (node.graphNodeId === activeFocusNodeId ? 16 : 12),
        id: "taxonomy-leaf-focus-halos",
        pickable: false,
        radiusUnits: "pixels",
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
        getLineColor: [247, 250, 255, 255],
        getLineWidth: 1,
        getPosition: (node) => [node.position.x, node.position.y],
        getRadius: (node) => node.radius,
        id: "taxonomy-leaf-points",
        lineWidthUnits: "pixels",
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
        radiusUnits: "pixels",
        stroked: true,
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
          const target = viewState.target ?? initialViewport.target;
          const nextZoom = Array.isArray(viewState.zoom)
            ? (viewState.zoom[0] ?? initialViewport.zoom)
            : (viewState.zoom ?? initialViewport.zoom);

          const nextViewport = {
            target: [
              target[0] ?? initialViewport.target[0],
              target[1] ?? initialViewport.target[1],
              target[2] ?? 0,
            ],
            zoom: nextZoom,
          } satisfies LeafOrthographicViewport;

          onViewportFrameChange?.(nextViewport);
          publishViewport(nextViewport);
        }}
        viewState={{ target: [...viewState.target], zoom: viewState.zoom }}
        views={leafView}
      />
    </div>
  );
}
