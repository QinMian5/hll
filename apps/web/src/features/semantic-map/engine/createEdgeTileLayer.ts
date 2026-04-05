// abstract: Deck.gl path-layer factory for semantic-map local card-edge rendering.
// out_of_scope: Tile query orchestration and point-detail panel interactions.

import { PathLayer } from "@deck.gl/layers";

import type { SemanticMapTileViewModel } from "../data/mappers";

type SemanticMapEdgeViewModel = SemanticMapTileViewModel["edges"][number];

export function createEdgeTileLayer(
  tile: SemanticMapTileViewModel | null,
): PathLayer<SemanticMapEdgeViewModel> {
  return new PathLayer<SemanticMapEdgeViewModel>({
    data: tile?.edges ?? [],
    getColor: [78, 95, 114, 200],
    getPath: (edge) => [edge.sourcePosition, edge.targetPosition],
    getWidth: (edge) => 1 + edge.strength * 2,
    id: tile
      ? `semantic-map-edges-${tile.version}-${tile.semanticLevel}-${tile.tile.z}-${tile.tile.x}-${tile.tile.y}`
      : "semantic-map-edges-empty",
    pickable: false,
    widthMinPixels: 1,
  });
}
