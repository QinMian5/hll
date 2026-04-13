// abstract: deck.gl scene assembly for taxonomy leaf point, edge, and card rendering.
// out_of_scope: Taxonomy data fetching and page-shell overlays.

import { OrthographicView } from "@deck.gl/core";
import { LineLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import { DeckGL } from "@deck.gl/react";
import { useMemo } from "react";

import type {
  LeafHoverState,
  LeafOrthographicViewport,
  LeafSceneCardNode,
  LeafSceneModel,
} from "./leafSceneTypes";

interface LeafDeckSceneProps {
  readonly onHoverChange: (hoverState: LeafHoverState | null) => void;
  readonly onViewportChange: (viewport: LeafOrthographicViewport) => void;
  readonly hoveredNodeId: number | null;
  readonly scene: LeafSceneModel;
  readonly viewport: LeafOrthographicViewport;
}

const leafView = new OrthographicView({
  controller: true,
  flipY: true,
  id: "taxonomy-leaf-view",
});

export function LeafDeckScene({
  onHoverChange,
  onViewportChange,
  hoveredNodeId,
  scene,
  viewport,
}: LeafDeckSceneProps) {
  const highlightedEdgeIds = useMemo(
    () =>
      hoveredNodeId ? (scene.edgeIdsByNodeId.get(hoveredNodeId) ?? null) : null,
    [hoveredNodeId, scene.edgeIdsByNodeId],
  );
  const highlightedNodeIds = useMemo(() => {
    if (!hoveredNodeId) {
      return null;
    }

    const neighborNodeIds =
      scene.neighborNodeIdsByNodeId.get(hoveredNodeId) ?? new Set<number>();
    return new Set([hoveredNodeId, ...neighborNodeIds]);
  }, [hoveredNodeId, scene.neighborNodeIdsByNodeId]);
  const hoveredCardNodes = useMemo(
    () =>
      hoveredNodeId
        ? scene.cardNodes.filter((node) => node.graphNodeId === hoveredNodeId)
        : [],
    [hoveredNodeId, scene.cardNodes],
  );
  const connectedCardNodes = useMemo(() => {
    if (!hoveredNodeId || !highlightedNodeIds) {
      return [];
    }

    return scene.cardNodes.filter(
      (node) =>
        node.graphNodeId !== hoveredNodeId &&
        highlightedNodeIds.has(node.graphNodeId),
    );
  }, [highlightedNodeIds, hoveredNodeId, scene.cardNodes]);
  const mutedCardNodes = useMemo(() => {
    if (!hoveredNodeId || !highlightedNodeIds) {
      return [];
    }

    return scene.cardNodes.filter(
      (node) => !highlightedNodeIds.has(node.graphNodeId),
    );
  }, [highlightedNodeIds, hoveredNodeId, scene.cardNodes]);

  const layers = useMemo(
    () => [
      new LineLayer({
        data: scene.edges,
        getColor: hoveredNodeId ? [180, 194, 219, 48] : [180, 194, 219, 168],
        getSourcePosition: (edge) => [edge.source.x, edge.source.y],
        getTargetPosition: (edge) => [edge.target.x, edge.target.y],
        getWidth: (edge) => (hoveredNodeId ? 1 : 1 + edge.strength * 1.25),
        id: "taxonomy-leaf-edges",
        pickable: false,
        widthUnits: "pixels",
      }),
      new LineLayer({
        data:
          hoveredNodeId && highlightedEdgeIds
            ? scene.edges.filter((edge) => highlightedEdgeIds.has(edge.id))
            : [],
        getColor: [102, 132, 181, 214],
        getSourcePosition: (edge) => [edge.source.x, edge.source.y],
        getTargetPosition: (edge) => [edge.target.x, edge.target.y],
        getWidth: (edge) => 2 + edge.strength * 1.5,
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
                ? [111, 135, 176, 235]
                : [160, 182, 219, 210]
              : [180, 194, 219, 72]
            : node.scope === "inner"
              ? [111, 135, 176, 235]
              : [160, 182, 219, 190],
        getLineColor: [245, 249, 255, 245],
        getLineWidth: 1,
        getPosition: (node) => [node.position.x, node.position.y],
        getRadius: (node) => node.radius,
        id: "taxonomy-leaf-points",
        lineWidthUnits: "pixels",
        pickable: false,
        radiusUnits: "pixels",
        stroked: true,
      }),
      new TextLayer<LeafSceneCardNode>({
        background: true,
        backgroundBorderRadius: 18,
        backgroundPadding: [16, 14],
        characterSet: "auto",
        data: !hoveredNodeId ? scene.cardNodes : [],
        fontFamily:
          '"Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"',
        getAlignmentBaseline: "center",
        getBackgroundColor: (node: LeafSceneCardNode) =>
          node.scope === "inner" ? [255, 255, 255, 250] : [239, 245, 252, 252],
        getColor: (node: LeafSceneCardNode) =>
          node.scope === "inner" ? [34, 59, 96, 255] : [50, 71, 99, 255],
        getPixelOffset: [0, 0],
        getPosition: (node: LeafSceneCardNode) => [
          node.position.x,
          node.position.y,
        ],
        getSize: 14,
        getText: (node: LeafSceneCardNode) => node.label,
        getTextAnchor: "middle",
        id: "taxonomy-leaf-cards-neutral",
        lineHeight: 1.2,
        maxWidth: 12.5,
        pickable: true,
        sizeUnits: "pixels",
        wordBreak: "break-word",
        onHover: (info) => {
          const card = info.object ?? null;
          if (!card || !info.viewport) {
            onHoverChange(null);
            return;
          }

          const [anchorX, anchorCenterY] = info.viewport.project([
            card.position.x,
            card.position.y,
            0,
          ]);

          onHoverChange({
            anchorX,
            anchorBottomY: anchorCenterY + card.size.height / 2,
            anchorTopY: anchorCenterY - card.size.height / 2,
            card,
          });
        },
      }),
      new TextLayer<LeafSceneCardNode>({
        background: true,
        backgroundBorderRadius: 18,
        backgroundPadding: [16, 14],
        characterSet: "auto",
        data: mutedCardNodes,
        fontFamily:
          '"Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"',
        getAlignmentBaseline: "center",
        getBackgroundColor: [232, 238, 247, 92],
        getColor: [100, 116, 139, 88],
        getPixelOffset: [0, 0],
        getPosition: (node: LeafSceneCardNode) => [
          node.position.x,
          node.position.y,
        ],
        getSize: 14,
        getText: (node: LeafSceneCardNode) => node.label,
        getTextAnchor: "middle",
        id: "taxonomy-leaf-cards-muted",
        lineHeight: 1.2,
        maxWidth: 12.5,
        pickable: true,
        sizeUnits: "pixels",
        wordBreak: "break-word",
        onHover: (info) => {
          const card = info.object ?? null;
          if (!card || !info.viewport) {
            onHoverChange(null);
            return;
          }

          const [anchorX, anchorCenterY] = info.viewport.project([
            card.position.x,
            card.position.y,
            0,
          ]);

          onHoverChange({
            anchorX,
            anchorBottomY: anchorCenterY + card.size.height / 2,
            anchorTopY: anchorCenterY - card.size.height / 2,
            card,
          });
        },
      }),
      new TextLayer<LeafSceneCardNode>({
        background: true,
        backgroundBorderRadius: 18,
        backgroundPadding: [16, 14],
        characterSet: "auto",
        data: connectedCardNodes,
        fontFamily:
          '"Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"',
        getAlignmentBaseline: "center",
        getBackgroundColor: (node: LeafSceneCardNode) =>
          node.scope === "inner" ? [250, 253, 255, 250] : [235, 242, 250, 250],
        getColor: (node: LeafSceneCardNode) =>
          node.scope === "inner" ? [30, 41, 59, 234] : [41, 55, 78, 236],
        getPixelOffset: [0, 0],
        getPosition: (node: LeafSceneCardNode) => [
          node.position.x,
          node.position.y,
        ],
        getSize: 14,
        getText: (node: LeafSceneCardNode) => node.label,
        getTextAnchor: "middle",
        id: "taxonomy-leaf-cards-connected",
        lineHeight: 1.2,
        maxWidth: 12.5,
        pickable: true,
        sizeUnits: "pixels",
        wordBreak: "break-word",
        onHover: (info) => {
          const card = info.object ?? null;
          if (!card || !info.viewport) {
            onHoverChange(null);
            return;
          }

          const [anchorX, anchorCenterY] = info.viewport.project([
            card.position.x,
            card.position.y,
            0,
          ]);

          onHoverChange({
            anchorX,
            anchorBottomY: anchorCenterY + card.size.height / 2,
            anchorTopY: anchorCenterY - card.size.height / 2,
            card,
          });
        },
      }),
      new TextLayer<LeafSceneCardNode>({
        background: true,
        backgroundBorderRadius: 18,
        backgroundPadding: [16, 14],
        characterSet: "auto",
        data: hoveredCardNodes,
        fontFamily:
          '"Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"',
        getAlignmentBaseline: "center",
        getBackgroundColor: [255, 255, 255, 255],
        getColor: (node: LeafSceneCardNode) =>
          node.scope === "inner" ? [15, 23, 42, 255] : [26, 38, 58, 255],
        getPixelOffset: [0, 0],
        getPosition: (node: LeafSceneCardNode) => [
          node.position.x,
          node.position.y,
        ],
        getSize: 14,
        getText: (node: LeafSceneCardNode) => node.label,
        getTextAnchor: "middle",
        id: "taxonomy-leaf-cards-hovered",
        lineHeight: 1.2,
        maxWidth: 12.5,
        pickable: true,
        sizeUnits: "pixels",
        wordBreak: "break-word",
        onHover: (info) => {
          const card = info.object ?? null;
          if (!card || !info.viewport) {
            onHoverChange(null);
            return;
          }

          const [anchorX, anchorCenterY] = info.viewport.project([
            card.position.x,
            card.position.y,
            0,
          ]);

          onHoverChange({
            anchorX,
            anchorBottomY: anchorCenterY + card.size.height / 2,
            anchorTopY: anchorCenterY - card.size.height / 2,
            card,
          });
        },
      }),
    ],
    [
      highlightedEdgeIds,
      highlightedNodeIds,
      hoveredCardNodes,
      hoveredNodeId,
      onHoverChange,
      connectedCardNodes,
      mutedCardNodes,
      scene.cardNodes,
      scene.edges,
      scene.pointNodes,
    ],
  );

  return (
    <div className="absolute inset-0" data-testid="taxonomy-leaf-renderer">
      <DeckGL
        layers={layers}
        onViewStateChange={({ viewState }) => {
          const target = viewState.target ?? viewport.target;
          const nextZoom = Array.isArray(viewState.zoom)
            ? (viewState.zoom[0] ?? viewport.zoom)
            : (viewState.zoom ?? viewport.zoom);

          onViewportChange({
            target: [
              target[0] ?? viewport.target[0],
              target[1] ?? viewport.target[1],
              target[2] ?? 0,
            ],
            zoom: nextZoom,
          });
        }}
        viewState={{ target: [...viewport.target], zoom: viewport.zoom }}
        views={leafView}
      />
    </div>
  );
}
