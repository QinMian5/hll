// abstract: Deck.gl text-layer factory for semantic-map label tiles.
// out_of_scope: Query orchestration and semantic-level state selection.

import { TextLayer } from "@deck.gl/layers";

import type { SemanticMapTileViewModel } from "../data/mappers";

type LabelDatum = SemanticMapTileViewModel["labels"][number];

function getLabelPosition(label: LabelDatum): [number, number] {
  return [label.position[0] ?? 0, label.position[1] ?? 0];
}

export function createLabelTileLayer(
  tile: SemanticMapTileViewModel | null,
): TextLayer<LabelDatum> {
  return new TextLayer<LabelDatum>({
    data: tile?.labels ?? [],
    getAlignmentBaseline: "center",
    getColor: [16, 35, 59, 255],
    getPosition: getLabelPosition,
    getSize: (label) => label.fontSize,
    getText: (label) => label.text,
    getTextAnchor: "middle",
    id: tile
      ? `semantic-map-labels-${tile.version}-${tile.semanticLevel}-${tile.tile.z}-${tile.tile.x}-${tile.tile.y}`
      : "semantic-map-labels-empty",
    pickable: false,
    sizeUnits: "pixels",
  });
}
