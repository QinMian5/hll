// abstract: Shared constants and defaults for the deck.gl-backed taxonomy leaf renderer.
// out_of_scope: Query orchestration and scene-layer instantiation.

import type { LayoutPoint } from "../layout/taxonomyLayoutTypes";
import type { LeafOrthographicViewport } from "./leafSceneTypes";

export const LEAF_CARD_ACTIVATION_ZOOM = 0.85;
export const LEAF_HYDRATION_OVERSCAN = 160;
export const LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS = 48;

export function buildDefaultLeafViewport(
  center: LayoutPoint,
): LeafOrthographicViewport {
  return {
    target: [center.x, center.y, 0],
    zoom: 0,
  };
}
