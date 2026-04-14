// abstract: deck.gl scene assembly for taxonomy leaf point, edge, and card rendering.
// out_of_scope: Taxonomy data fetching and page-shell overlays.

import { OrthographicView } from "@deck.gl/core";
import { LineLayer, ScatterplotLayer } from "@deck.gl/layers";
import { DeckGL } from "@deck.gl/react";
import { useMemo } from "react";

import type {
  LeafOrthographicViewport,
  LeafSceneModel,
} from "./leafSceneTypes";
import { useLeafViewportStore } from "./useLeafViewportStore";

interface LeafDeckSceneProps {
  readonly onViewportFrameChange?: (viewport: LeafOrthographicViewport) => void;
  readonly onViewportChange: (viewport: LeafOrthographicViewport) => void;
  readonly hoveredNodeId: number | null;
  readonly initialViewport: LeafOrthographicViewport;
  readonly scene: LeafSceneModel;
}

const leafView = new OrthographicView({
  controller: true,
  flipY: true,
  id: "taxonomy-leaf-view",
});

export function LeafDeckScene({
  onViewportFrameChange,
  onViewportChange,
  hoveredNodeId,
  initialViewport,
  scene,
}: LeafDeckSceneProps) {
  const { publishViewport, viewState } = useLeafViewportStore({
    initialViewport,
    onViewportSnapshotChange: onViewportChange,
  });
  const highlightedEdges = useMemo(
    () =>
      hoveredNodeId
        ? (scene.highlightEdgesByNodeId.get(hoveredNodeId) ?? [])
        : [],
    [hoveredNodeId, scene.highlightEdgesByNodeId],
  );
  const highlightedNodeIds = useMemo(
    () =>
      hoveredNodeId
        ? (scene.focusNodeIdsByNodeId.get(hoveredNodeId) ?? null)
        : null,
    [hoveredNodeId, scene.focusNodeIdsByNodeId],
  );
  const layers = useMemo(
    () => [
      new LineLayer({
        data: scene.edges,
        getColor: hoveredNodeId ? [186, 206, 239, 58] : [191, 210, 244, 132],
        getSourcePosition: (edge) => [edge.source.x, edge.source.y],
        getTargetPosition: (edge) => [edge.target.x, edge.target.y],
        getWidth: () => 1,
        id: "taxonomy-leaf-edges",
        pickable: false,
        widthUnits: "pixels",
      }),
      new LineLayer({
        data: highlightedEdges,
        getColor: [116, 152, 217, 214],
        getSourcePosition: (edge) => [edge.source.x, edge.source.y],
        getTargetPosition: (edge) => [edge.target.x, edge.target.y],
        getWidth: () => 1.5,
        id: "taxonomy-leaf-highlight-edges",
        pickable: false,
        widthUnits: "pixels",
      }),
      new ScatterplotLayer({
        data: scene.pointNodes,
        filled: true,
        getFillColor: (node) =>
          highlightedNodeIds
            ? highlightedNodeIds.has(node.graphNodeId)
              ? node.scope === "inner"
                ? [120, 163, 243, 255]
                : [144, 185, 247, 232]
              : [180, 198, 229, 84]
            : node.scope === "inner"
              ? [120, 163, 243, 252]
              : [144, 185, 247, 224],
        getLineColor: [247, 250, 255, 255],
        getLineWidth: 1,
        getPosition: (node) => [node.position.x, node.position.y],
        getRadius: (node) => node.radius,
        id: "taxonomy-leaf-points",
        lineWidthUnits: "pixels",
        pickable: false,
        radiusUnits: "pixels",
        stroked: true,
      }),
    ],
    [
      highlightedEdges,
      highlightedNodeIds,
      hoveredNodeId,
      scene.edges,
      scene.pointNodes,
    ],
  );

  return (
    <div className="absolute inset-0" data-testid="taxonomy-leaf-renderer">
      <DeckGL
        layers={layers}
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
