// abstract: Semantic zoom helpers driven by backend-defined level metadata.
// out_of_scope: Tile fetching, deck.gl rendering, and React state orchestration.

import type { SemanticMapLevelViewModel } from "../data/mappers";

export interface SemanticZoomState {
  readonly activeLevel: SemanticMapLevelViewModel;
  readonly baseLevel: number;
}

interface GetSemanticZoomStateArgs {
  readonly defaultSemanticLevel: number;
  readonly levels: readonly SemanticMapLevelViewModel[];
  readonly zoom: number;
}

function getDistanceToZoomBand(
  zoom: number,
  level: SemanticMapLevelViewModel,
): number {
  if (zoom < level.minZoom) {
    return level.minZoom - zoom;
  }

  if (zoom > level.maxZoom) {
    return zoom - level.maxZoom;
  }

  return 0;
}

export function getSemanticZoomState({
  defaultSemanticLevel,
  levels,
  zoom,
}: GetSemanticZoomStateArgs): SemanticZoomState {
  const orderedLevels = [...levels].sort(
    (left, right) => left.level - right.level,
  );
  const fallbackLevel =
    orderedLevels.find((level) => level.level === defaultSemanticLevel) ??
    orderedLevels[0];

  if (!fallbackLevel) {
    throw new Error(
      "Semantic zoom requires at least one configured semantic level.",
    );
  }

  const levelForZoom = orderedLevels.find(
    (level) => zoom >= level.minZoom && zoom <= level.maxZoom,
  );

  if (levelForZoom) {
    return {
      activeLevel: levelForZoom,
      baseLevel: levelForZoom.level,
    };
  }

  if (zoom < fallbackLevel.minZoom) {
    return {
      activeLevel: fallbackLevel,
      baseLevel: fallbackLevel.level,
    };
  }

  const nearestLevel = orderedLevels.reduce((best, current) => {
    const bestDistance = getDistanceToZoomBand(zoom, best);
    const currentDistance = getDistanceToZoomBand(zoom, current);

    return currentDistance < bestDistance ? current : best;
  }, fallbackLevel);

  return {
    activeLevel: nearestLevel,
    baseLevel: nearestLevel.level,
  };
}
