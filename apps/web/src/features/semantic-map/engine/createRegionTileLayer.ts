// abstract: Deck.gl polygon-layer factory for semantic-map region tiles.
// out_of_scope: Query orchestration and page-level view-state ownership.

import { PolygonLayer } from "@deck.gl/layers";

import type { SemanticMapTileViewModel } from "../data/mappers";

type RegionDatum = SemanticMapTileViewModel["regions"][number];

function getRegionFillColor(
  displayRank: number,
): [number, number, number, number] {
  const emphasis = Math.max(0, 255 - displayRank * 18);

  return [emphasis, 132, 92 + displayRank * 6, 150];
}

export function createRegionTileLayer(
  tile: SemanticMapTileViewModel | null,
): PolygonLayer<RegionDatum> {
  return new PolygonLayer<RegionDatum>({
    data: tile?.regions ?? [],
    filled: true,
    getFillColor: (region) => getRegionFillColor(region.displayRank),
    getLineColor: [15, 23, 42, 160],
    getLineWidth: 1,
    getPolygon: (region) => region.geometry.coordinates,
    id: tile
      ? `semantic-map-regions-${tile.version}-${tile.semanticLevel}-${tile.tile.z}-${tile.tile.x}-${tile.tile.y}`
      : "semantic-map-regions-empty",
    lineWidthMinPixels: 1,
    pickable: true,
    stroked: true,
  });
}
