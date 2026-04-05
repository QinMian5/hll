// abstract: Deck.gl scatterplot-layer factory for semantic-map card points.
// out_of_scope: Query orchestration and point-detail panel state ownership.

import { ScatterplotLayer } from "@deck.gl/layers";

import type {
  SemanticMapPointViewModel,
  SemanticMapTileViewModel,
} from "../data/mappers";

export function isSemanticMapPointDatum(
  value: unknown,
): value is SemanticMapPointViewModel {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.nodeId === "number" &&
    Array.isArray(candidate.position)
  );
}

export function createPointTileLayer(
  tile: SemanticMapTileViewModel | null,
): ScatterplotLayer<SemanticMapPointViewModel> {
  return new ScatterplotLayer<SemanticMapPointViewModel>({
    data: tile?.points ?? [],
    filled: true,
    getFillColor: [17, 94, 166, 240],
    getLineColor: [255, 255, 255, 220],
    getLineWidth: 1,
    getPosition: (point) => point.position,
    getRadius: 5,
    id: tile
      ? `semantic-map-points-${tile.version}-${tile.semanticLevel}-${tile.tile.z}-${tile.tile.x}-${tile.tile.y}`
      : "semantic-map-points-empty",
    lineWidthMinPixels: 1,
    pickable: true,
    radiusMinPixels: 4,
    stroked: true,
  });
}
