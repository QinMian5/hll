// abstract: Projection helpers for DOM overlays anchored to taxonomy leaf world coordinates.
// out_of_scope: deck.gl layer construction and rich-text rendering.

import type { LayoutViewport } from "../layout/taxonomyLayoutTypes";
import type { LeafOrthographicViewport } from "./leafSceneTypes";

interface ProjectedPoint {
  readonly x: number;
  readonly y: number;
}

function scaleFromZoom(zoom: number) {
  return 2 ** zoom;
}

export function projectLeafWorldPoint(
  canvas: LayoutViewport,
  viewport: LeafOrthographicViewport,
  point: { readonly x: number; readonly y: number },
): ProjectedPoint {
  const [targetX, targetY] = viewport.target;
  const scale = scaleFromZoom(viewport.zoom);

  return {
    x: (point.x - targetX) * scale + canvas.width / 2,
    y: (point.y - targetY) * scale + canvas.height / 2,
  };
}
