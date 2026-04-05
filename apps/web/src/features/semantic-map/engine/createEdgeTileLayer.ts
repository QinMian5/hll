// abstract: Deck.gl path-layer factory for semantic-map local card-edge rendering.
// out_of_scope: Tile query orchestration and point-detail panel interactions.

import { PathLayer } from "@deck.gl/layers";

import type { SemanticMapTileViewModel } from "../data/mappers";

type SemanticMapEdgeViewModel = SemanticMapTileViewModel["edges"][number];

export function createEdgeTileLayer(
  tile: SemanticMapTileViewModel | null,
  options: {
    readonly selectedNodeId: number | null;
  },
): PathLayer<SemanticMapEdgeViewModel> {
  const { selectedNodeId } = options;

  return new PathLayer<SemanticMapEdgeViewModel>({
    data: tile?.edges ?? [],
    getColor:
      selectedNodeId === null
        ? [78, 95, 114, 200]
        : (edge) =>
            edge.sourceNodeId === selectedNodeId ||
            edge.targetNodeId === selectedNodeId
              ? [208, 94, 31, 235]
              : [123, 136, 148, 80],
    getPath: (edge) => [edge.sourcePosition, edge.targetPosition],
    getWidth:
      selectedNodeId === null
        ? (edge) => 1 + edge.strength * 2
        : (edge) =>
            edge.sourceNodeId === selectedNodeId ||
            edge.targetNodeId === selectedNodeId
              ? 2 + edge.strength * 3
              : 0.6,
    id: tile
      ? `semantic-map-edges-${tile.version}-${tile.semanticLevel}-${tile.tile.z}-${tile.tile.x}-${tile.tile.y}`
      : "semantic-map-edges-empty",
    pickable: false,
    widthMinPixels: 1,
  });
}
